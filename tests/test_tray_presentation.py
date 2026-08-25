"""Presentation guarantees for the tray controls.

These pin properties whose ABSENCE was the defect. The genre list did not look
wrong because a rule said the wrong thing — it looked wrong because no rule said
anything, so the browser's own control chrome showed through. A test that only
checked for the presence of a `.genre-item` rule would have passed throughout.

The same shape appears in the dismissal assertions: an overlay with no affordance
has no failing selector to find, only a missing one.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / 'web'
INDEX = WEB / 'index.html'
OVERLAYS_CSS = WEB / 'assets' / 'overlays.css'


def strip_comments(source: str) -> str:
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return source


def block_after(source: str, opener: str) -> str:
    """The body of the rule introduced by `opener`, to its eight-space close.

    Line-anchored on purpose. `\\n\\s{8}\\}` looks equivalent and is not — `\\s`
    matches newlines, so the capture ends mid-block and the assertions built on
    it stop being able to fail.
    """
    match = re.search(re.escape(opener) + r'(.*?)^ {8}\}', source, flags=re.S | re.M)
    assert match, f'no block found for {opener!r}'
    return match.group(1)


@pytest.fixture(scope='module')
def index() -> str:
    return strip_comments(INDEX.read_text())


@pytest.fixture(scope='module')
def markup() -> str:
    """Markup with comments removed, for locating and inspecting panels.

    Comments must go here as much as anywhere else. The comment explaining why
    `aria-live` moved off the panel contains the string `aria-live`, and the
    assertion that it is no longer on the panel matched that prose — passing
    judgement on a note about the fix rather than on the fix.
    """
    return strip_comments(INDEX.read_text())


@pytest.fixture(scope='module')
def overlays() -> str:
    return strip_comments(OVERLAYS_CSS.read_text())


# ---------------------------------------------------------------------------
# The shared tray choice
# ---------------------------------------------------------------------------


def test_tray_choice_resets_the_browsers_button_chrome(index):
    """The properties whose absence produced white system buttons.

    `.genre-item` became a `<button>` during the tray conversion while its rule
    went on describing `<div>` rows — padding, cursor, white-space, font-size.
    None of those override a user agent's control appearance, so the entries
    rendered as the browser drew them.
    """
    body = block_after(index, '.genre-item {')
    for prop in ('display:', 'background:', 'border:', 'border-radius:', 'font:'):
        assert prop in body, (
            f'.genre-item declares no {prop.rstrip(":")}; without it the browser '
            f'supplies its own and the entry renders as a system button'
        )
    assert 'inline-block' not in body, (
        'an explicit display is the point — inline-block is the default that '
        'produced the ragged inline run'
    )


def test_tray_choice_count_has_rules_of_its_own(index):
    """`Action794`. Two spans, no styling, no separation."""
    body = block_after(index, '.genre-item__count {')
    assert 'font-size:' in body
    assert 'color:' in body

    empty = block_after(index, '.genre-item__count:empty {')
    assert 'display: none' in empty, (
        'an empty count must leave the layout entirely, or the flex gap reserves '
        'space beside a badge that renders nothing'
    )


def test_both_tray_bodies_lay_their_choices_out(index):
    """The other half of the ragged layout: inline children in a block box."""
    body = block_after(index, '.genre-tray__body,\n        .server-tray__body {')
    assert 'flex' in body
    assert 'wrap' in body


def test_the_tray_choice_is_shared_by_both_trays(index):
    """Genre and server destinations are the same control.

    Asserted so a future change to one is known to reach the other — styling
    them apart is how they drift, and the server tray inherited its broken
    appearance precisely because it reuses this class.
    """
    assert "className = 'genre-item server-item'" in index, (
        'populateServerTray() no longer builds its destinations with '
        '.genre-item; the two trays will now drift apart'
    )


# ---------------------------------------------------------------------------
# One dismissal affordance, at every width
# ---------------------------------------------------------------------------


def has_class(chunk: str, name: str) -> bool:
    """Whether the markup contains an element carrying exactly this class.

    Membership in the whitespace-separated class list, not a substring and not a
    `\\b` match. Both weaker forms accept `modal__head-x`: substring obviously,
    and `\\b` because a hyphen is a non-word character, so a word boundary sits
    between `head` and `-x`. Renaming a required region away therefore passed a
    test whose whole job was to require it.
    """
    return any(name in match.group(1).split() for match in re.finditer(r'class="([^"]*)"', chunk))


def overlay_panels(raw: str) -> dict[str, tuple[str, str]]:
    """Each overlay panel, keyed by accessible name, as (root class, markup).

    The root's class decides which affordances the panel needs, so it is carried
    alongside rather than inferred from the panel.
    """
    panels = {}
    for match in re.finditer(r'<div class="((?:sheet|modal)[^"]*)"[^>]*>', raw):
        root_class = match.group(1)
        if '__' in root_class.split()[0]:
            continue  # a panel/backdrop/body, not an overlay root
        start, depth, i, n = match.start(), 0, match.start(), len(raw)
        while i < n:
            if raw.startswith('<div', i):
                depth += 1
            elif raw.startswith('</div>', i):
                depth -= 1
                if depth == 0:
                    break
            i += 1
        chunk = raw[start : i + 6]
        panel = re.search(
            r'<div class="(?:sheet|modal)__panel[^"]*"(.*?)role="dialog"', chunk, flags=re.S
        )
        if not panel:
            continue
        name = re.search(r'aria-label(?:ledby)?="([^"]+)"', chunk)
        panels[name.group(1) if name else f'panel@{start}'] = (root_class, chunk)
    return panels


def test_every_panel_carries_a_dismissal_affordance(markup):
    """An overlay that wears both shapes needs BOTH affordances, not either.

    "grip or close" is the intuitive rule and it is wrong. The two are not
    alternatives offered at the same moment — each is hidden at the width where
    the other is shown. A tray's grip is hidden above 768px, because a mouse has
    no drag to make; its close button is hidden below, because the handle is the
    thumb-reachable affordance. So a panel carrying only a grip has nothing at
    pointer widths, and one carrying only a close has nothing on touch.

    That is exactly what the Actions tray did: grip only, so between 769px and
    992px — where the hamburger still shows it — it opened as a centred dialog
    with no handle and no close button. Backdrop and Escape worked; nothing on
    screen said so.

    A plain `.modal` is the exception. It is a centred dialog at every width and
    never shows a grip, so its close button alone is the whole affordance.
    """
    panels = overlay_panels(markup)
    assert len(panels) >= 5, f'expected the overlay panels, found {list(panels)}'
    for name, (root_class, chunk) in panels.items():
        has_grip = has_class(chunk, 'sheet__grip')
        has_close = has_class(chunk, 'overlay__close')
        wears_both_shapes = 'sheet' in root_class or 'modal--tray-on-touch' in root_class

        if wears_both_shapes:
            assert has_grip and has_close, (
                f'overlay {name!r} presents as a tray on touch and a dialog on a '
                f'pointer device, so it needs a grab handle AND a close button — '
                f'each is hidden at the width where the other is shown. '
                f'grip={has_grip}, close={has_close}'
            )
        else:
            assert has_close, (
                f'overlay {name!r} is a centred dialog at every width and never '
                f'shows a grip, so it must carry a close button'
            )


def test_a_tray_hides_its_close_button_on_touch(overlays):
    """The handle is the affordance there; two ways to close is worse than one.

    Both shapes: a `.sheet` below the breakpoint IS a tray, which is what the
    pointer block says by only turning it into a dialog above 768px.
    """
    touch = re.search(r'@media \(max-width: 767px\) \{(.*)$', overlays, flags=re.S)
    assert touch, 'the touch block is gone'
    rule = re.search(r'([^{}]*)\{\s*display: none;\s*\}', touch.group(1))
    assert rule, 'nothing is hidden in the touch block'
    selectors = touch.group(1)
    assert '.sheet .overlay__close' in selectors, (
        'a .sheet still shows its close button on touch beside the grab handle'
    )
    assert '.modal--tray-on-touch .overlay__close' in selectors


def test_the_breakpoint_pair_has_not_drifted(overlays):
    """The rule that hides one affordance and the rule that shows the other.

    They must sit at the same boundary. Split apart, a width exists where an
    overlay has neither — which is exactly what happened to the sort/genre
    hand-off at 992px and 768px.
    """
    pointer = re.search(r'@media \(min-width: (\d+)px\)', overlays)
    touch = re.search(r'@media \(max-width: (\d+)px\)', overlays)
    assert pointer and touch, 'both breakpoint blocks must exist'
    assert int(pointer.group(1)) == int(touch.group(1)) + 1, (
        f'the pointer block starts at {pointer.group(1)}px and the touch block '
        f'ends at {touch.group(1)}px; widths between have neither rule'
    )


# ---------------------------------------------------------------------------
# The roulette
# ---------------------------------------------------------------------------


def test_roulette_carries_the_three_regions(markup):
    """A modifier alone would produce an overlay with no way out.

    `.modal--tray-on-touch` hides the close button on touch. On a panel with no
    grab handle — and a backdrop that deliberately does not dismiss — that
    leaves nothing at all.
    """
    entry = overlay_panels(markup).get('roulette-title')
    assert entry, 'the roulette panel is not named by roulette-title'
    _, panel = entry
    for region in ('sheet__grip', 'modal__head', 'modal__body'):
        assert has_class(panel, region), f'the roulette panel has no {region}'


def test_roulette_head_is_not_inside_its_body(markup):
    """The drag region and the scrolling region must stay separate.

    `touch-action: none` on the head is honoured only while the head is not
    itself inside the scroller. Nesting hands the gesture back to the browser as
    a scroll — silently, with no visual difference on a desktop.
    """
    _, panel = overlay_panels(markup)['roulette-title']
    body_start = panel.index('modal__body')
    assert panel.index('modal__head') < body_start
    assert not has_class(panel[body_start:], 'modal__head'), (
        'the roulette head is nested inside its scrolling body'
    )


def test_roulette_is_a_tray_on_touch(markup):
    assert 'modal modal--tray-on-touch" x-show="rouletteOpen"' in markup


def test_roulette_panel_declares_no_settled_transform(index):
    """`transform: translateY(30px)` used to sit on this panel.

    The transition classes outrank it while a transition runs, so it looked
    harmless — then Alpine removed them at the end of the entrance and the
    settled panel dropped 30px.
    """
    body = block_after(index, '.roulette-modal {')
    assert 'transform' not in body, (
        'the roulette panel sets its own transform, which takes effect once the '
        'transition classes are removed'
    )


def test_roulette_announces_its_status_not_its_dialog(markup):
    """The live region wraps the content that changes, not the whole panel."""
    _, panel = overlay_panels(markup)['roulette-title']
    assert 'aria-live' in panel
    head_end = panel.index('modal__body')
    assert 'aria-live' not in panel[:head_end], (
        'aria-live is on the panel or head rather than on the region whose content updates'
    )


# ---------------------------------------------------------------------------
# The head divider
# ---------------------------------------------------------------------------


def test_divider_is_scoped_away_from_artwork_only(index, overlays):
    """Removed where the head crosses a picture; kept where it separates bands."""
    scoped = block_after(index, '.modal__fixed .modal__head {')
    assert 'border-bottom: none' in scoped

    base = re.search(r'\.modal__head \{(.*?)\n\}', overlays, flags=re.S)
    assert base, '.modal__head base rule not found'
    assert 'border-bottom: 1px' in base.group(1), (
        'the base divider was removed rather than scoped; that flattens the '
        'trailer, roulette and server switcher to fix the detail overlay'
    )


def test_the_region_divider_survives(index):
    """`.modal-header`'s border marks where holding still becomes scrolling."""
    body = block_after(index, '.modal-header {')
    assert 'border-bottom: 1px' in body
