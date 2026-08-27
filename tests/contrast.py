"""Contrast arithmetic, written once for every test that needs it.

Two test files check that something stays readable over the detail overlay's
backdrop artwork — the muted metadata in `test_overlay_layering.py`, the grab
handle in `test_overlay_markup.py` — and both have to composite the same image
over the same surface at the same opacity to do it. Two hand-copied sRGB curves
drift, and the symptom is two tests disagreeing about whether the same pair of
colours passes, which is worse than either being wrong on its own.

This is not a general colour library. It is the four operations those
assertions need, with the reasoning that makes them the right four:

  - `srgb_to_linear` / `relative_luminance` — WCAG 2.x, unchanged.
  - `contrast_ratio` — the (L1 + 0.05) / (L2 + 0.05) ratio.
  - `composite` — `opacity` on an element blends it with what is behind it, so
    the effective background of text over the artwork is the artwork's colour
    mixed into the panel surface. Reading the artwork's own colour and comparing
    against that would be wrong by the whole of the surface.

WHAT THE WORST CASE IS. The artwork is an image from the user's library, so the
colour behind the text is not ours to choose. Every caller here composites
WHITE — the brightest an image can be — rather than a representative backdrop.
A bar met only by the average image is a bar that fails for somebody, and it
fails invisibly: the person who opened that item sees soft grey text and has no
way to know the app intended otherwise.

CI has no browser, so these are assertions about the source values, not about
pixels. They pin the decision; they cannot prove the render.
"""

import re

Rgb = tuple[float, float, float]


def parse_hex(value: str) -> Rgb:
    """`#abc` or `#aabbcc` (with or without the hash) to an RGB triple."""
    digits = value.strip().lstrip('#')
    if len(digits) == 3:
        digits = ''.join(character * 2 for character in digits)
    assert re.fullmatch(r'[0-9a-fA-F]{6}', digits), f'not a hex colour: {value!r}'
    return tuple(int(digits[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def srgb_to_linear(channel: float) -> float:
    """One 0-255 channel to linear light."""
    fraction = channel / 255
    if fraction <= 0.03928:
        return fraction / 12.92
    return ((fraction + 0.055) / 1.055) ** 2.4


def relative_luminance(colour: Rgb) -> float:
    red, green, blue = (srgb_to_linear(channel) for channel in colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(one: Rgb, other: Rgb) -> float:
    first = relative_luminance(one)
    second = relative_luminance(other)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def composite(front: Rgb, back: Rgb, alpha: float) -> Rgb:
    """`front` drawn over `back` at `alpha` — what `opacity` actually produces.

    The result is what anything ON TOP of the front layer is really sitting on,
    which is the number a contrast check needs. Comparing against `front` itself
    would ignore the surface entirely and overstate every result.
    """
    return tuple(  # type: ignore[return-value]
        alpha * f + (1 - alpha) * b for f, b in zip(front, back, strict=True)
    )


WHITE: Rgb = (255, 255, 255)

# The bars, named so a caller states which one it means rather than a bare
# float. WCAG 2.1: 4.5:1 for body text, 3:1 for a user interface component.
TEXT_BAR = 4.5
CONTROL_BAR = 3.0


def declared_value(css: str, selector: str, prop: str) -> str:
    """The value of `prop` in the rule for `selector`, comments already gone.

    Fails loudly when the rule or the property is missing rather than skipping
    the assertion built on it. A renamed selector is exactly the moment somebody
    should re-read why the value was what it was, and a pattern that quietly
    matches nothing is worse than no test at all.
    """
    rule = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', css)
    assert rule, f'no rule for `{selector}`; if it was renamed, update this test'
    found = re.search(rf'(?<![-\w]){re.escape(prop)}\s*:\s*([^;}}]+)', rule.group(1))
    assert found, f'`{selector}` declares no `{prop}`'
    return found.group(1).strip()


def declared_token(css: str, name: str) -> str:
    """The value of a custom property declared anywhere in `css`."""
    found = re.search(rf'{re.escape(name)}\s*:\s*([^;}}]+)', css)
    assert found, f'`{name}` is not declared'
    return found.group(1).strip()
