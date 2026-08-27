"""A pill control's label stays legible while its fill changes underneath it.

Three controls in the header — the two tabs, the sort buttons and the genre
button — switch between the neutral fill and the accent fill by toggling
`.active`. Their labels sit at opposite ends of the brightness range because
their fills do: white on `--tab-bg`, black on the accent.

The defect this pins out: `transition: all` swept `color` into the fade, so
selecting a tab drove its label from white to black over the same 300ms that
drove its pill from `#333` to `#e5a00d`. Halfway through, the label is mid-grey
and the pill is still substantially accent-coloured, and mid-grey on Plex yellow
is barely readable. Deselection is worse — the label goes light while the pill
is still yellow, which is how it was reported: white text on the yellow button.

It is the duration that makes this a test rather than something a human catches.
A 300ms wash is obvious when you know to look and deniable when you do not, it
only exists on the frames between two correct states, and every screenshot ever
taken of these controls shows them resting and correct.

CI has no browser, so what is pinned here is the source decision the appearance
depends on: the label colour is declared, and it is not transitioned. A control
that is accent-filled at rest never crosses and is deliberately not covered.

These are source assertions, not behavior tests. Behavior needs a browser.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / 'web' / 'index.html'

# The controls that cross between the two fills, by their base selector exactly
# as authored. Explicit rather than discovered: the interesting property is
# "changes fill AND label together", and a scan for the accent fill alone would
# sweep in the controls that wear it at rest — which have no crossing, and no
# reason to be constrained.
CROSSING = [
    '.tab',
    '.sort-button, .genre-button',
]

# Accent-filled at rest. Named here so the exclusion is a decision on the record
# rather than an absence, and asserted below to stay out of CROSSING.
ALWAYS_ACCENT = [
    '.genre-badge',
    '.scroll-to-top',
    '.roulette-close-btn',
]


def strip_css_comments(source: str) -> str:
    """Drop block comments.

    Not cosmetic. The comment above `.tab` explains the defect by quoting it —
    it contains the words `all`, `color` and `transition` in the exact shapes
    asserted against below. An assertion that matches the comment explaining why
    something was removed, rather than the code, is a test that cannot fail.
    """
    return re.sub(r'/\*.*?\*/', ' ', source, flags=re.S)


def stylesheet(html: str) -> str:
    """Every `<style>` block in the document, concatenated.

    HTML comments come out first. A comment in the head refers to "the `<style>`
    below" in prose, and the tag scan happily opens on that — capturing the
    commentary as the first rule of the stylesheet.
    """
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.S)
    blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, flags=re.S)
    assert blocks, 'no <style> block in index.html'
    return strip_css_comments('\n'.join(blocks))


def brace_end(css: str, open_at: int) -> int:
    """Index of the `}` closing the block that opens at `open_at`."""
    depth = 0
    for index in range(open_at, len(css)):
        if css[index] == '{':
            depth += 1
        elif css[index] == '}':
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError('unbalanced braces in the stylesheet')


def rules(css: str, start: int = 0, end: int | None = None) -> list[tuple[str, str]]:
    """(selector, body) for every style rule, descending into at-rules.

    Media queries hold the responsive copies of these rules, so a flat scan of
    the top level would miss any override living inside one.
    """
    end = len(css) if end is None else end
    found: list[tuple[str, str]] = []
    index = start
    segment = start
    while index < end:
        char = css[index]
        if char == '{':
            selector = re.sub(r'\s+', ' ', css[segment:index]).strip()
            close = brace_end(css, index)
            if selector.startswith('@'):
                found.extend(rules(css, index + 1, close))
            else:
                found.append((selector, css[index + 1 : close]))
            index = close + 1
            segment = index
        elif char == '}':
            index += 1
            segment = index
        else:
            index += 1
    return found


def declarations(body: str) -> dict[str, str]:
    """A rule body as property -> value. Later wins, as the cascade has it."""
    out = {}
    for part in body.split(';'):
        if ':' not in part:
            continue
        prop, _, value = part.partition(':')
        out[prop.strip().lower()] = re.sub(r'\s+', ' ', value).strip()
    return out


@pytest.fixture(scope='module')
def css() -> str:
    return stylesheet(INDEX.read_text())


@pytest.fixture(scope='module')
def by_selector(css) -> dict[str, dict[str, str]]:
    """Every rule for a selector, merged in document order — later wins.

    Merged rather than replaced because these selectors appear more than once:
    `.scroll-to-top` is declared at the top level and resized again inside a
    media query. Keeping only the last occurrence would read the responsive
    override as the whole rule and lose the fill it was never restating. It also
    means a media query that puts `transition: all` back fails here, which is
    the direction that matters.
    """
    merged: dict[str, dict[str, str]] = {}
    for selector, body in rules(css):
        merged.setdefault(selector, {}).update(declarations(body))
    return merged


def rule(by_selector: dict[str, dict[str, str]], selector: str) -> dict[str, str]:
    """Fail loudly when a selector is gone rather than passing on nothing.

    A rename is exactly the moment someone should re-read this decision, and a
    test whose pattern quietly matches nothing is worse than no test at all.
    """
    assert selector in by_selector, (
        f'no rule for `{selector}` in web/index.html. If it was renamed or '
        f'split, update CROSSING here — and re-read why the label colour on '
        f'these controls is switched rather than eased.'
    )
    return by_selector[selector]


# ---------------------------------------------------------------------------
# The label is declared, and it is not eased
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('selector', CROSSING)
def test_a_crossing_pill_declares_its_resting_label_colour(by_selector, selector):
    """Inheritance makes the resting colour invisible where it is decided.

    The selected rule names a colour; a base rule that names none reads as
    though the label has no colour of its own, and the pair only makes sense to
    someone who already knows the answer.
    """
    assert 'color' in rule(by_selector, selector), (
        f'`{selector}` sets a label colour when selected but leaves its resting '
        f'colour to inheritance'
    )


@pytest.mark.parametrize('selector', CROSSING)
def test_a_crossing_pill_does_not_transition_its_label_colour(by_selector, selector):
    """The whole fix. `color` must be switched, never interpolated."""
    transition = rule(by_selector, selector).get('transition')
    assert transition, f'`{selector}` declares no transition'

    properties = {part.strip().split(' ')[0] for part in transition.split(',')}

    assert 'all' not in properties, (
        f'`{selector}` transitions `all`, which sweeps in `color`. That is the '
        f'defect: the label crosses between white and black through mid-grey '
        f'while the fill is still accent-coloured. Name the properties.'
    )
    assert 'color' not in properties, (
        f'`{selector}` transitions `color`. Between the neutral and accent '
        f'fills every midpoint of that interpolation is illegible.'
    )


@pytest.mark.parametrize('selector', CROSSING)
def test_the_selected_state_still_sets_the_label_colour(by_selector, selector):
    """The other half: switching only works if there is something to switch to.

    Without this, deleting `color` from the selected rule passes every
    assertion above while restoring the illegible state from the other side —
    black-on-accent becomes white-on-accent, permanently.
    """
    selected = ', '.join(part + '.active' for part in selector.split(', '))
    declared = rule(by_selector, selected)
    assert 'color' in declared, f'`{selected}` no longer sets a label colour'
    assert 'var(--primary-color)' in declared.get('background-color', ''), (
        f'`{selected}` no longer takes the accent fill, so `{selector}` may no '
        f'longer be a crossing control at all'
    )


# ---------------------------------------------------------------------------
# The list stays honest in both directions
# ---------------------------------------------------------------------------


def test_every_accent_toggling_pill_is_covered(by_selector):
    """A pill added later must not quietly escape the rule.

    Narrower than scanning for the accent fill: only a rule whose selector is a
    base plus `.active` is toggling between two fills. A control that wears the
    accent at rest cannot match, which is why this does not drag the excluded
    ones back in.
    """
    for selector, declared in by_selector.items():
        parts = [part.strip() for part in selector.split(',')]
        if not all(part.endswith('.active') for part in parts):
            continue
        if 'var(--primary-color)' not in declared.get('background-color', ''):
            continue
        if 'color' not in declared:
            continue
        base = ', '.join(part[: -len('.active')] for part in parts)
        assert base in CROSSING, (
            f'`{selector}` toggles both the accent fill and its label colour, '
            f'so `{base}` crosses between fills and belongs in CROSSING'
        )


@pytest.mark.parametrize('selector', ALWAYS_ACCENT)
def test_an_always_accent_control_is_not_constrained(by_selector, selector):
    """Accent-filled at rest means there is no crossing to make illegible.

    Asserted rather than assumed, because a control that acquires a neutral
    resting state later becomes a crossing control, and this is where that
    shows up.
    """
    assert selector not in CROSSING
    declared = rule(by_selector, selector)
    assert 'var(--primary-color)' in declared.get('background-color', ''), (
        f'`{selector}` no longer wears the accent at rest. If it now toggles '
        f'into it, it crosses between fills and belongs in CROSSING.'
    )
