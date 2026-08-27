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


SHARED_HEAD = '.sheet__head, .modal__head'


def css_rules(source: str, indent: int = 0) -> dict[str, str]:
    """Every rule at ONE nesting level, keyed by its selector list.

    Keyed by the whole list rather than found by substring, because the two are
    not the same question here. `.modal__head` appears both alone and as the
    second line of `.sheet__head, .modal__head`, so a search for the standalone
    rule finds the shared one first and asserts against the wrong body — which
    is a test that fails for a reason that has nothing to do with the code.

    `indent` selects the level: 0 for top-level rules, 4 for those inside a
    media query. Whitespace in the key is collapsed, so a selector list broken
    across lines is looked up as it reads.
    """
    pad = ' ' * indent
    pattern = rf'^{pad}([^\s@{{][^{{}}]*?)\{{(.*?)^{pad}\}}'
    return {
        re.sub(r'\s+', ' ', match.group(1)).strip(): match.group(2)
        for match in re.finditer(pattern, source, flags=re.S | re.M)
    }


def css_block(source: str, selector: str, indent: int = 0) -> str:
    rules = css_rules(source, indent)
    assert selector in rules, f'no rule found for {selector!r}'
    return rules[selector]


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


@pytest.fixture(scope='module')
def overlays_js() -> str:
    return strip_comments((WEB / 'assets' / 'overlays.js').read_text())


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
# The trailer
# ---------------------------------------------------------------------------


def test_trailer_is_a_tray_on_touch(markup):
    assert 'modal modal--tray-on-touch" x-show="trailerOpen"' in markup


def test_trailer_panel_declares_no_background(overlays):
    """The regression that started this: `.modal__panel--video` set `#000`.

    That made the trailer the one panel in the app not drawn from --surface — a
    pure black head beside every other overlay's #2a2a2a, and a per-server accent
    that stopped at this overlay's border. The modifier sizes the panel and does
    nothing else; black belongs to the well the video sits in.
    """
    body = css_block(overlays, '.modal__panel--video')
    assert 'background' not in body, (
        '.modal__panel--video paints its own panel. An overlay that does not use '
        'the shared surface stops matching the app the first time a token moves, '
        'and nothing fails when it does.'
    )


def _declared_background(body: str) -> str:
    match = re.search(r'background(?:-color)?:\s*([^;]+);', body)
    assert match, f'no background declared in {body!r}'
    return match.group(1).strip()


def test_the_well_and_its_loading_state_are_the_same_colour(index):
    """A PAIR, and the defect is only visible on the frames between two states.

    `.trailer-loading` was `rgba(26, 26, 26, 0.7)`, which composites over the
    well's black to #121212 — so the two were different blacks with a seam
    between them, and the region changed colour at the instant the iframe faded
    in. That instant is when a viewer is looking hardest at it, and it is also
    the one moment no screenshot of a resting overlay can show.

    Compared as declared values rather than as "both are black": a translucent
    colour is the exact way this broke, and `rgba(0, 0, 0, 0.3)` would read as
    black to any test asking for the word.
    """
    well = _declared_background(block_after(index, '.trailer-container {'))
    loading = _declared_background(block_after(index, '.trailer-loading {'))
    assert well == loading, (
        f'the video well is {well} and its loading state is {loading}. They must '
        f'be the same opaque value or the overlay changes colour as the video '
        f'arrives.'
    )
    assert 'rgba' not in well, (
        f'{well} is translucent, so it composites against whatever is behind it '
        f'rather than stating a colour'
    )


def test_trailer_spinner_takes_its_colours_from_tokens(index):
    """Its track was `rgba(229, 160, 13, 0.2)` — Plex yellow at 20%.

    On Jellyfin and Emby the ring was therefore drawn in another server's theme,
    with nothing on screen or in the source to say so. A hardcoded colour on a
    themed component is invisible on the theme it was picked from, which is the
    only one anyone tests in.
    """
    body = block_after(index, '.trailer-spinner {')
    assert 'rgba(' not in body and '#' not in body, f'.trailer-spinner hardcodes a colour: {body!r}'
    assert 'var(--primary-color)' in body, 'the leading edge should follow the server accent'


def test_trailer_spinner_does_not_duplicate_the_apps_keyframe(index):
    """`@keyframes trailer-spin` was byte-identical to `spinner-rotate`."""
    assert '@keyframes trailer-spin' not in index
    assert 'spinner-rotate' in block_after(index, '.trailer-spinner {')


def test_the_video_well_is_capped_by_width_not_height(index):
    """`max-height` on an aspect-ratio box is the trap this avoids.

    It clamps the height while the width goes on filling its container, so the
    ratio breaks and the video letterboxes inside its own well — silently, and
    only on the short viewports (a landscape phone) nobody checks. Deriving the
    width from the height budget keeps the box 16:9 at every size.
    """
    body = block_after(index, '.trailer-container {')
    assert 'aspect-ratio: 16 / 9' in body
    assert 'max-height' not in body, (
        'a max-height here clamps the height and leaves the width filling its '
        'container, which breaks the ratio instead of bounding the box'
    )
    assert re.search(r'width:\s*min\(100%,\s*calc\(', body), (
        'the well is not capped by the height available, so a landscape phone '
        'pushes the video out of the panel'
    )


# ---------------------------------------------------------------------------
# Region order
# ---------------------------------------------------------------------------


def test_a_panel_with_a_grip_orders_its_three_regions(markup):
    """Grip, then head, then body — and the body last is the load-bearing part.

    A head that follows its body is a head the drag gesture still matches and the
    viewer still sees, so nothing looks wrong; but `touch-action: none` is
    honoured only while the head is not inside the scroller, and the ordering is
    what keeps them siblings in practice. Asserted for every panel that has a
    grip rather than for the overlay that needed it first — the trailer's regions
    arrived with `modal--tray-on-touch`, and the next one's must too.
    """
    seen = 0
    for name, (_, chunk) in overlay_panels(markup).items():
        if 'sheet__grip' not in chunk:
            continue
        seen += 1
        grip = chunk.index('sheet__grip')
        head = re.search(r'(?:sheet|modal)__head', chunk)
        body = re.search(r'(?:sheet|modal)__body', chunk)
        assert head, f'overlay {name!r} has a grip and no head'
        assert body, f'overlay {name!r} has a grip and no body'
        assert grip < head.start() < body.start(), (
            f'overlay {name!r} orders its regions grip@{grip}, '
            f'head@{head.start()}, body@{body.start()}'
        )
    assert seen >= 5, f'expected every gripped panel, found {seen}'


# ---------------------------------------------------------------------------
# The head divider
# ---------------------------------------------------------------------------


def test_divider_is_scoped_away_from_artwork_only(index, overlays):
    """Removed where the head crosses a picture; kept where it separates bands."""
    scoped = block_after(index, '.modal__fixed .modal__head {')
    assert 'border-bottom: none' in scoped

    assert 'border-bottom: 1px' in css_block(overlays, SHARED_HEAD), (
        'the base divider was removed rather than scoped; that flattens the '
        'trailer, roulette and server switcher to fix the detail overlay'
    )


def test_the_region_divider_survives(index):
    """`.modal-header`'s border marks where holding still becomes scrolling."""
    body = block_after(index, '.modal-header {')
    assert 'border-bottom: 1px' in body


# ---------------------------------------------------------------------------
# One distance from the handle to the title
#
# Every overlay wearing the grab handle holds its title the same distance below
# it. The distance is measured to the GLYPH, not to the top of the line box, so
# it has two terms and each was wrong independently: the two heads declared
# 14px and 16px of top padding, and `.modal-title` set `line-height: 1.1`
# against the 1.5 every other title inherits. They cancelled on the detail
# overlay and compounded on the roulette, which is why it never presented as a
# clean offset anyone would go looking for.
# ---------------------------------------------------------------------------

VERTICAL_PADDING = ('padding:', 'padding-top', 'padding-bottom', 'padding-block')


def test_the_two_heads_cannot_declare_different_vertical_padding(overlays):
    """Not "equal values" — one rule, so there are no two values to compare.

    Asserting the numbers match would pass the day someone changes both to the
    same wrong thing and, more to the point, would still permit two rules. Two
    rules is the defect: they were 14px and 16px, and nothing said they were
    related.
    """
    shared = css_block(overlays, SHARED_HEAD)
    assert 'padding-top' in shared and 'padding-bottom' in shared, (
        'the shared head rule no longer sets the vertical padding both heads depend on'
    )

    for selector in ('.sheet__head', '.modal__head'):
        own = css_block(overlays, selector)
        for prop in VERTICAL_PADDING:
            assert prop not in own, (
                f'`{selector}` sets its own {prop}, so the tray and the dialog can '
                f'again hold their titles different distances below the same '
                f'grab handle. Vertical padding belongs to the shared rule; '
                f'this one carries the horizontal inset only.'
            )


TITLE_SELECTORS = ('.sheet__title', '.modal__head h2', '.modal-title', '#roulette-title')


def test_no_overlay_title_sets_its_own_line_height(index, overlays):
    """The half-leading is half the gap, and the only half that hides.

    `line-height: 1.1` on `.modal-title` sat inside a rule of four dead
    declarations, so it read as part of a definition rather than as an override.
    Nothing about the padding — the thing anyone checks — looked wrong.
    """
    for source, name in ((index, 'index.html'), (overlays, 'overlays.css')):
        for match in re.finditer(r'([^{}]+)\{([^{}]*)\}', source):
            selector, body = match.group(1).strip(), match.group(2)
            if 'line-height' not in body:
                continue
            for title in TITLE_SELECTORS:
                # A trailing boundary, so `.modal-title-section` is not
                # `.modal-title`. It is a real class in this markup.
                if re.search(re.escape(title) + r'(?![\w-])', selector):
                    raise AssertionError(
                        f'{name}: `{selector}` sets line-height on an overlay '
                        f'title. The gap below the grab handle is measured to '
                        f'the glyph, so half-leading is part of it — an '
                        f'override here moves the title without touching any '
                        f'padding. Let it inherit.'
                    )


def test_the_handle_less_bump_reaches_both_heads(overlays):
    """The compensation belongs to every head that just lost a handle."""
    bump = '.sheet__grip ~ .sheet__head, .sheet__grip ~ .modal__head'
    assert bump in css_rules(overlays, indent=4), (
        'the padding that stands in for the hidden grab handle no longer names '
        'both heads. Naming `.sheet__head` alone leaves the detail and roulette '
        'dialogs — whose handles the same block hides — without it.'
    )
    assert '.sheet__grip + .modal__head' not in overlays, (
        'the adjacent combinator misses the detail overlay: `.modal-backdrop-art` '
        'sits between its grip and its head. Use `~`.'
    )


def test_hiding_the_handle_and_replacing_its_spacing_stay_together(overlays):
    """One breakpoint, or a width exists where the title sits 4px high.

    The same pairing rule the dismissal affordances live under. A sibling
    selector matches a `display: none` grip, so the selector says only "has a
    grip in the markup" — the media query supplies "and it is hidden", and it
    has to be the one doing the hiding.
    """
    pointer = re.search(r'@media \(min-width: 768px\) \{(.*?)^\}', overlays, flags=re.S | re.M)
    assert pointer, 'the pointer-width block is gone'
    rules = css_rules(pointer.group(1), indent=4)

    assert 'display: none' in rules.get('.sheet__grip', ''), (
        'this block no longer hides the grab handle, so the padding that '
        'compensates for hiding it is compensating for nothing'
    )
    assert any('~ .modal__head' in selector for selector in rules), (
        'the handle is hidden at one breakpoint and its spacing replaced at '
        'another; every width between shows a title too close to nothing'
    )


# ---------------------------------------------------------------------------
# A tray on touch actually slides
#
# The modifier and the transition class land on the SAME element — Alpine puts
# `overlay-shut` on the overlay root, which is where `modal--tray-on-touch`
# already is. A descendant combinator between them asks for an ancestor that
# does not exist, so the rule matches nothing, and the generic dialog rule
# (`.overlay-shut .modal__panel { transform: scale(0.96) }`) wins by default.
#
# Nothing errors. On a desktop the result is correct anyway. On a phone the
# detail overlay and the roulette scaled like centred dialogs while every other
# tray slid up from the edge — and it reads as the animation feeling wrong,
# never as a selector that matched zero elements.
# ---------------------------------------------------------------------------

TRANSITION_STATES = ('overlay-opening', 'overlay-shut', 'overlay-shown')


def test_tray_on_touch_transitions_are_compound_selectors(overlays):
    """`.overlay-shut.modal--tray-on-touch`, never `.overlay-shut .modal--…`."""
    for state in TRANSITION_STATES:
        assert f'.{state} .modal--tray-on-touch' not in overlays, (
            f'`.{state} .modal--tray-on-touch` has a descendant combinator, but '
            f'Alpine puts `{state}` on the same element the modifier is on. '
            f'This selector matches nothing, and the dialog scale rule wins — '
            f'the tray stops sliding and nothing reports an error.'
        )
        assert f'.{state}.modal--tray-on-touch .modal__panel' in overlays, (
            f'the tray-on-touch `{state}` rule is gone; a dialog that becomes a '
            f'tray on a phone will scale instead of sliding'
        )


def test_the_tray_on_touch_panel_translates_rather_than_scales(overlays):
    """The whole point of the modifier: a tray arrives from the bottom edge."""
    touch = re.search(r'@media \(max-width: 767px\) \{(.*?)^\}', overlays, flags=re.S | re.M)
    assert touch, 'the touch block is gone'
    rules = css_rules(touch.group(1), indent=4)

    shut = rules.get('.overlay-shut.modal--tray-on-touch .modal__panel', '')
    shown = rules.get('.overlay-shown.modal--tray-on-touch .modal__panel', '')
    assert 'translateY(100%)' in shut, 'a tray-on-touch panel no longer starts off the bottom edge'
    assert 'translateY(0)' in shown, 'a tray-on-touch panel no longer settles at the edge'


def test_releasing_the_scroll_lock_does_not_animate_the_page(overlays_js):
    """Restoring the scroll position is a correction, not a journey.

    Releasing the body from `position: fixed` drops the document to scroll 0 for
    a frame; this call puts it back. `index.html` sets `scroll-behavior: smooth`
    and the two-argument `scrollTo(x, y)` obeys it, so the restore ANIMATED —
    measured at 30,000px into the library, the page streamed back over ~1.5
    seconds after every dismissal. It was reported as the tray shooting up the
    screen on close, and the tray is not the thing that moves.
    """
    release = re.search(
        r"root\.classList\.remove\('is-overlay-open'\);(.*?)\n            \}",
        overlays_js,
        flags=re.S,
    )
    assert release, 'the scroll-lock release block was not found'
    body = release.group(1)
    assert 'window.scrollTo(0,' not in body, (
        'the release uses the two-argument scrollTo, which obeys '
        '`scroll-behavior: smooth` and animates the restore over ~1.5s'
    )
    assert "behavior: 'instant'" in body, (
        'the scroll restore no longer states an instant behavior, so it inherits '
        "the document's smooth scrolling"
    )
