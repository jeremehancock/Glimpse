"""Markup guarantees for the overlay system that nothing else can catch.

Every assertion here corresponds to a failure that is INVISIBLE in the browser
you are testing in. An overlay missing its dialog role opens and looks perfect;
a drag region nested inside its scroller looks perfect too, on a desktop, where
nobody drags. These are the cases a human passes and a test does not.

They are markup assertions, not behavior tests. Behavior needs a browser; what
is pinned here is the shape the behavior depends on.
"""

import re
from pathlib import Path

import pytest

from contrast import (
    CONTROL_BAR,
    WHITE,
    composite,
    contrast_ratio,
    declared_token,
    declared_value,
    parse_hex,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / 'web'
INDEX = WEB / 'index.html'


@pytest.fixture(scope='module')
def html() -> str:
    return INDEX.read_text()


def strip_comments(source: str) -> str:
    """Drop HTML and block comments.

    Every assertion about a retired implementation has to run against code, not
    prose. The comments explaining WHY something was removed name the thing that
    was removed — which is the point of them, and would otherwise fail the very
    test that guards the removal.
    """
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return source


def overlay_panels(html: str) -> list[str]:
    """The opening tag of every overlay panel in the document."""
    return re.findall(r'<div[^>]*class="[^"]*(?:sheet__panel|modal__panel)[^"]*"[^>]*>', html)


# --------------------------------------------------------------------------
# The focus trap
# --------------------------------------------------------------------------


def test_every_overlay_panel_declares_itself_a_dialog(html):
    """The single most important assertion in this file.

    The focus manager finds its subjects by `role="dialog"` — deliberately, so
    an overlay is managed by being marked up correctly rather than by being
    registered somewhere. The cost of that design is this failure mode: an
    overlay added without the role opens, renders identically, and leaves a
    keyboard user on the page behind the backdrop with no way in and no way out.

    Nothing errors. Nothing looks wrong. Only a keyboard finds it.
    """
    panels = overlay_panels(html)
    assert panels, 'no overlay panels found — has the markup moved?'

    for panel in panels:
        assert 'role="dialog"' in panel, f'panel is not focus-managed: {panel[:120]}'
        assert 'aria-modal="true"' in panel, f'panel is not modal: {panel[:120]}'
        assert 'tabindex="-1"' in panel, (
            f'panel cannot receive focus, so the manager cannot move focus into it: {panel[:120]}'
        )


def test_every_overlay_panel_is_labelled(html):
    """A dialog announced as "dialog" and nothing else tells a screen reader
    user an overlay opened, but not which one."""
    for panel in overlay_panels(html):
        assert 'aria-label="' in panel or 'aria-labelledby="' in panel, (
            f'unlabelled dialog: {panel[:120]}'
        )


# --------------------------------------------------------------------------
# The drag gesture
# --------------------------------------------------------------------------


def test_drag_regions_are_not_the_scroller(html):
    """The grip and head must be SIBLINGS of the body, never ancestors.

    They carry `touch-action: none` to stop the browser claiming a downward drag
    as a scroll, and the browser honours that only if the element is not itself
    the scrolling container. Nesting the head inside the scrolling body returns
    the gesture to the browser silently — the tray simply stops being
    swipe-dismissable, with no error and no visual difference.
    """
    grip = r'<div[^>]*class="[^"]*sheet__grip[^"]*"[^>]*>(.*?)</div>'
    for match in re.finditer(grip, html, re.S):
        assert 'sheet__body' not in match.group(1), 'a grip contains the scrolling body'

    # A head may contain a title and a close button, never the body.
    for match in re.finditer(
        r'<div[^>]*class="[^"]*(?:sheet__head|modal__head)[^"]*"[^>]*>(.*?)</div>\s*<', html, re.S
    ):
        assert 'sheet__body' not in match.group(1)
        assert 'modal__body' not in match.group(1)


def test_every_tray_has_a_grab_handle(html):
    """The handle is the dismissal affordance on touch. A tray without one
    offers no visible way to close itself where the close button is hidden."""
    sheets = re.findall(r'<div class="sheet"[^>]*>.*?(?=<div class="sheet"|\Z)', html, re.S)
    for sheet in sheets:
        assert 'sheet__grip' in sheet, 'a tray has no grab handle'


# --------------------------------------------------------------------------
# The retired implementations
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    'retired',
    [
        'genre-drawer',
        'genre-dropdown',
        'modal-overlay',
        'modal-content',
        'trailer-modal-overlay',
        'trailer-modal-content',
        'roulette-overlay',
    ],
)
def test_superseded_overlay_markup_is_gone(html, retired):
    """Each of these was one of six bespoke overlay implementations.

    Left in place they are not merely dead weight: they are a working second
    implementation for someone to extend by accident, and the genre pair in
    particular had already drifted apart in behavior.
    """
    # The names may appear in prose explaining the removal.
    code = strip_comments(html)
    assert f'"{retired}' not in code
    assert f'.{retired}' not in code


def test_genre_filter_has_exactly_one_implementation(html):
    """The clearest duplication in the original file: a desktop dropdown and a
    phone drawer building the same list from the same data, separately."""
    assert html.count('genre-tray__body') >= 1
    # Comments stripped: the surviving builder's docstring names both of the
    # functions it replaced, which is worth keeping and is not a definition.
    assert 'function updateGenreDropdown' not in strip_comments(html)
    assert 'function updateGenreDrawer' not in strip_comments(html)


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------


def test_alpine_is_vendored_not_fetched_from_a_cdn(html):
    """A CDN script is a network dependency that fails exactly when the network
    is what failed — which is the one moment an offline-capable PWA is supposed
    to still work."""
    assert (WEB / 'assets' / 'alpine.min.js').is_file()
    assert 'src="/assets/alpine.min.js"' in html

    for match in re.finditer(r'<script[^>]*src="([^"]+)"', html):
        src = match.group(1)
        assert not src.startswith('http'), f'remote script: {src}'
        assert '//' not in src.lstrip('/'), f'protocol-relative script: {src}'


def test_overlay_assets_are_cached_by_the_service_worker():
    """Vendoring Alpine only buys offline capability if it is also cached."""
    sw = (WEB / 'sw.js').read_text()
    for asset in (
        '/assets/alpine.min.js',
        '/assets/overlays.js',
        '/assets/tokens.css',
        '/assets/overlays.css',
    ):
        assert asset in sw, f'{asset} is not cached; the app breaks offline'


def test_reduced_motion_is_handled_once_and_app_wide():
    """An overlay moves the largest area of the screen of anything here, so it
    is the most consequential place to miss a motion preference. Stated once so
    a new overlay inherits it rather than having to remember."""
    tokens = (WEB / 'assets' / 'tokens.css').read_text()
    assert 'prefers-reduced-motion' in tokens
    assert '*,' in tokens, 'the reduced-motion rule is not app-wide'


def test_closing_overlays_stop_taking_clicks():
    """Alpine keeps an overlay displayed for the length of its leave animation.

    Without this the user dismisses an overlay, reaches for what is behind it,
    and the tap lands on a backdrop that is visually almost gone.
    """
    css = (WEB / 'assets' / 'overlays.css').read_text()
    closing = css[css.index('.overlay-closing {') :]
    assert 'pointer-events: none' in closing[: closing.index('}')]


def test_no_control_explains_itself_only_in_a_tooltip(html):
    """A tooltip is hover-and-fine-pointer only, so a reason attached to one is
    a reason no touch user ever receives — a dimmed control and silence."""
    for match in re.finditer(r'<[^>]*aria-disabled="true"[^>]*>', html):
        assert 'data-tooltip' not in match.group(0), (
            'a switched-off control explains itself only where touch cannot reach'
        )


# --------------------------------------------------------------------------
# Regressions from the first tray build
#
# Every test below corresponds to a bug that shipped to :dev and was found by
# hand, not by the suite. They are here because the suite passed while the app
# was broken — structure was asserted, behavior was not.
# --------------------------------------------------------------------------


def test_openmodal_selectors_match_the_markup(html):
    """The detail overlay and roulette both went blank because openModal()
    queried elements this change had renamed.

    `.modal-backdrop` became `.modal-backdrop-art` (the old name now belongs to
    the overlay system's scrim) and `.modal-body` became `.modal__body`. Both
    returned null, both threw, and roulette died with the detail view because it
    opens through the same function. Nothing in the suite noticed: the overlay
    was present and correctly attributed, which is all the markup tests looked
    at.

    Matched against the class attributes that actually exist in the markup —
    not against the file as text, which would find the name in a comment
    explaining the rename and pass while the app was broken.
    """
    code = strip_comments(html)

    present = set()
    # Authored markup.
    for attr in re.findall(r'class="([^"]*)"', code):
        present.update(attr.split())
    # Elements built at runtime — e.g. the retry button, whose querySelector is
    # an "already exists?" guard rather than a lookup of authored markup.
    for attr in re.findall(r'className\s*=\s*[\'"]([^\'"]*)[\'"]', code):
        present.update(attr.split())
    for attr in re.findall(r'classList\.add\(([^)]*)\)', code):
        present.update(re.findall(r'[\'"]([A-Za-z0-9_-]+)[\'"]', attr))

    queried = re.findall(r"querySelector(?:All)?\('([^']*\.modal[^']*)'\)", code)
    assert queried, 'no modal selectors found — has openModal moved?'

    for selector in queried:
        leaf = selector.split()[-1]
        for cls in re.findall(r'\.([A-Za-z0-9_-]+)', leaf):
            assert cls in present, (
                f'openModal queries {selector!r} but no element carries '
                f'class {cls!r} — querySelector returns null and openModal throws'
            )


def test_hamburger_keeps_its_own_styling(html):
    """`.mobile-menu-button` lost every rule it had.

    The script that stripped the retired `.mobile-menu` CSS matched on
    substrings, and `.mobile-menu-button` contains `.mobile-menu`. The button
    lost its `display: none` and appeared on desktop, where it opens a tray that
    is a touch shape.
    """
    assert '.mobile-menu-button {' in html, 'the hamburger has no styling at all'
    rule = html[html.index('.mobile-menu-button {') :]
    assert 'display: none' in rule[: rule.index('}')], (
        'the hamburger is not hidden by default, so it shows on desktop'
    )


def test_trays_become_dialogs_on_a_pointer_device():
    """A tray is a touch shape: bottom-docked, full-bleed, dragged away by a
    thumb. On a desktop it is a panel glued to the bottom of a large screen with
    a drag affordance nobody will use. The menu, genre and server overlays
    rendered that way at every width until this rule existed."""
    css = (WEB / 'assets' / 'overlays.css').read_text()
    assert '@media (min-width: 768px)' in css
    block = css[css.index('@media (min-width: 768px)') :]
    assert 'align-items: center' in block, 'trays do not centre on a pointer device'
    assert '.sheet__grip' in block, 'the grab handle is not hidden on a pointer device'


def test_actions_tray_does_not_duplicate_the_tab_switcher(html):
    """Switching content type is a horizontal swipe on the grid, and the header
    tabs are hidden at tray widths. Listing Movies / TV Shows in the tray made it
    look like the tray was the way to do it."""
    tray = re.search(r'aria-label="Actions".*?</template>', strip_comments(html), re.S)
    assert tray, 'Actions tray not found'
    assert 'data-content="movies"' not in tray.group(0), (
        'the Actions tray lists content-type tabs; swipe already does this'
    )


# --------------------------------------------------------------------------
# Page rules reaching into overlays
# --------------------------------------------------------------------------


def test_no_page_rule_hides_the_actions_overlays_controls(html):
    """The Actions overlay opened with its handle, its title, and nothing else.

    `.sort-toggle { display: none }` inside a mobile media query meant "hide the
    HEADER's sort controls". But the overlay's body IS a `.sort-toggle` — its
    only child — so the rule emptied the overlay it was never aimed at. Measured
    at 390px: the body was 20px tall, which was its own bottom padding.

    Nothing errored. The overlay animated in correctly and was correctly
    attributed; it simply had no contents. A rule that hides a page control has
    to say which one, or it reaches every copy of that markup in the document.
    """
    css = strip_comments(html)

    for match in re.finditer(r'([^{}]*)\{([^{}]*)\}', css):
        selectors, body = match.group(1), match.group(2)
        if 'display' not in body or 'none' not in body:
            continue
        for selector in selectors.split(','):
            selector = selector.strip()
            if not selector.endswith('.sort-toggle'):
                continue
            assert '.header-content' in selector, (
                f'{selector!r} hides every .sort-toggle in the document, '
                'including the Actions overlay body, which is one'
            )


def test_the_actions_overlays_trigger_appears_where_the_header_controls_leave(html):
    """There must be no width at which both are hidden.

    The header's sort controls withdrew at 992px and the hamburger only arrived
    at 768px, so between 769px and 992px a tablet had no sort, no genre filter
    and no server switch — and no trigger for the overlay that carries them.

    The two rules are one hand-off. Splitting them is silent: each rule looks
    correct on its own, and the gap only exists at widths nobody tests at.
    """
    css = strip_comments(html)

    media_block = r'@media[^{]*?max-width:\s*(\d+)px[^{]*?\{(.*?)\n        \}'
    blocks = [(int(m.group(1)), m.group(2)) for m in re.finditer(media_block, css, re.S)]

    def blocks_containing(selector: str) -> list[int]:
        return [width for width, body in blocks if re.search(re.escape(selector) + r'\s*\{', body)]

    sort_hidden = blocks_containing('.header-content .sort-toggle')
    trigger_shown = blocks_containing('.mobile-menu-button')

    assert sort_hidden, 'the header sort controls are never withdrawn'
    assert trigger_shown, 'the hamburger is never shown'

    # Asserted as CO-LOCATION, not as two numbers that happen to agree today.
    # The pair is one hand-off, and the only way to guarantee they cannot drift
    # apart is to require they be declared together. Comparing two breakpoints
    # would pass the moment someone moved one rule to a block that happens to
    # carry the same width, and would say nothing about the next edit to either.
    assert set(sort_hidden) == set(trigger_shown), (
        f'the header controls withdraw at {sort_hidden}px but the overlay '
        f'trigger appears at {trigger_shown}px. These are one hand-off and '
        'belong in the same media query — split apart, the widths between them '
        'have no way to sort, filter by genre or switch server, which is '
        'exactly what happened from 769px to 992px'
    )


def test_the_actions_overlay_stacks_its_controls(html):
    """The overlay reuses the header's markup, and the header lays it out as a
    horizontal ROW of pills.

    Left as a row inside a 390px overlay the four controls ran off the right
    edge — measured scrollWidth 524 against a client width of 388, putting
    "Switch server" and "Install App" outside the panel. This was invisible for
    as long as the block was hidden by the bug above, so fixing that one exposed
    this one.
    """
    css = strip_comments(html)
    rule = re.search(r'\.sheet__body \.sort-toggle\s*\{([^}]*)\}', css)
    assert rule, 'the Actions overlay does not restate its layout direction'
    assert 'column' in rule.group(1), (
        'the overlay lays its controls out as a row; they overflow the panel'
    )


# --------------------------------------------------------------------------
# The detail overlay's fixed region
# --------------------------------------------------------------------------


def test_the_item_identity_block_is_not_inside_the_scroller(html):
    """The poster, year, rating and trailer control must hold still.

    They were the first child of `.modal__body`, which is the scrolling region,
    so reading the summary carried away the very thing being read about.
    """
    code = strip_comments(html)
    body = re.search(r'<div class="modal__body">(.*?)\n            </div>', code, re.S)
    assert body, 'the detail overlay body was not found — has the markup moved?'
    assert 'modal-header' not in body.group(1), (
        'the item identity block is inside the scrolling body, so it scrolls away'
    )

    fixed = re.search(r'<div class="modal__fixed">(.*?)\n            </div>', code, re.S)
    assert fixed, 'the detail overlay has no fixed region'
    assert 'modal-header' in fixed.group(1), 'the identity block is not in the fixed region'


def test_the_fixed_region_is_not_itself_a_scroller():
    """`.modal__fixed` carries `touch-action: none` and is in the drag gesture's
    selector list. Both are honoured only while it is not the scrolling
    container.

    Giving it `overflow-y: auto` is the obvious way to stop a long title
    squeezing out the summary, and it would silently hand the downward swipe
    back to the browser — the same failure as nesting a head inside its body,
    reached from the other direction. The height is bounded by capping what
    grows inside it instead.
    """
    css = (WEB / 'assets' / 'overlays.css').read_text()
    rule = re.search(r'\.modal__fixed\s*\{([^}]*)\}', css)
    assert rule, '.modal__fixed has no rule in the overlay stylesheet'
    assert 'touch-action: none' in rule.group(1), (
        'the fixed region is not in the drag gesture, so it is a dead patch at the top of the tray'
    )
    assert 'overflow' not in rule.group(1), (
        'the fixed region is a scroller, which silently disables the drag gesture'
    )


def test_a_long_title_cannot_squeeze_out_the_scrolling_region(html):
    """With the title unclamped, a 13-line title left the scrolling region 20px
    tall — measured at 390x667. The poster has a fixed width and the metadata is
    short, so the title is the only part that can grow without limit."""
    css = strip_comments(html)
    rule = re.search(r'\.modal__fixed \.modal-title\s*\{([^}]*)\}', css)
    assert rule, 'the detail title is unbounded; a long one squeezes out the summary'
    assert 'line-clamp' in rule.group(1)


def test_the_backdrop_artwork_cannot_reach_the_scrolling_region(html):
    """It was `height: 280px` against the panel — a number sized for the desktop
    dialog, where the identity block happens to be about that tall.

    On a phone it overshot the head by 214px into the scrolling body, so the
    summary and cast slid beneath a stationary picture. Filling its container
    makes the extent a consequence of the layout instead of a constant that has
    to be re-guessed per viewport.
    """
    css = strip_comments(html)
    rule = re.search(r'\.modal-backdrop-art\s*\{([^}]*)\}', css)
    assert rule, 'the backdrop artwork has no rule'
    assert 'inset: 0' in rule.group(1), (
        'the artwork is sized independently of the fixed region, so it can '
        'extend into scrolling content'
    )
    assert not re.search(r'height:\s*\d', rule.group(1)), 'the artwork has a fixed height again'


def test_the_grab_handle_is_legible_on_both_surfaces_it_lands_on(html):
    """BOTH surfaces, in one assertion, because checking one is the defect.

    The handle can be drawn over two things: an overlay's own panel surface,
    which is every tray in the app, and the detail overlay's backdrop artwork
    composited over that same surface. It was `#4b4f57`, which is 1.75:1 against
    plain surface — below the 3:1 bar for a control, on every tray, for as long
    as there have been trays.

    That went unseen because the one place anyone had looked at this handle was
    the detail overlay, the only one with a picture behind it, and there the
    artwork was masked away from behind the handle. So the handle was never
    legible BECAUSE of that mask; it was legible in spite of being the wrong
    colour, in one overlay, by having its background deleted. The mask is gone
    and the colour carries itself now.

    Note the direction that makes the pair real: dimming the artwork moved the
    composite TOWARD a mid-grey handle, so the change that fixed the text made
    this worse. Contrast is a relation between two colours, not a fact about
    either, which is why both moved in one commit.
    """
    css = strip_comments(html)
    overlays = strip_comments((WEB / 'assets' / 'overlays.css').read_text())
    tokens = strip_comments((WEB / 'assets' / 'tokens.css').read_text())

    handle = parse_hex(declared_value(overlays, '.sheet__handle', 'background'))
    surface = parse_hex(declared_token(tokens, '--surface'))
    opacity = float(declared_value(css, '.modal-backdrop-art', 'opacity'))

    over_surface = contrast_ratio(handle, surface)
    assert over_surface >= CONTROL_BAR, (
        f'the grab handle is {over_surface:.2f}:1 on a plain tray, below '
        f'{CONTROL_BAR}:1. On touch it is the only affordance that dismisses a '
        f'tray by gesture.'
    )

    over_artwork = contrast_ratio(handle, composite(WHITE, surface, opacity))
    assert over_artwork >= CONTROL_BAR, (
        f'the grab handle is {over_artwork:.2f}:1 over the brightest backdrop '
        f'artwork, below {CONTROL_BAR}:1. Do not fix this by masking the '
        f'artwork away behind it — that is what made the handle unverified on '
        f'every other tray.'
    )


def test_every_tray_wears_the_same_handle(html):
    """One component, not one per overlay.

    Two trays are almost never on screen together, so a divergence here would
    never be noticed — it would simply drift, the same way `.sheet__head` and
    `.modal__head` drifted to 14px and 16px of padding while nothing said they
    were related. The colour is declared once and scoped to nothing.
    """
    overlays = strip_comments((WEB / 'assets' / 'overlays.css').read_text())
    css = strip_comments(html)

    declarations = re.findall(r'([^{}]*\.sheet__handle[^{}]*)\{([^}]*)\}', overlays + css)
    painted = [
        (selector.strip(), body)
        for selector, body in declarations
        if re.search(r'(?<![-\w])background(?:-color)?\s*:', body)
    ]
    assert len(painted) == 1, (
        f'the grab handle is painted by {len(painted)} rules '
        f'({[selector for selector, _ in painted]}). It is one control; an '
        f'overlay dressing its own copy differently is how the two drift.'
    )
    assert painted[0][0] == '.sheet__handle', (
        f'the handle colour is scoped to `{painted[0][0]}`, so it applies to '
        f'some trays and not others'
    )


def test_the_drag_gesture_selectors_all_exist_in_the_markup(html):
    """The gesture arms by `closest()` on a class list. A name in that list that
    no element carries is not an error — it simply never matches, and the region
    silently stops being draggable."""
    js = (WEB / 'assets' / 'overlays.js').read_text()
    call = re.search(r"closest\(\s*\n?\s*'([^']*)'\s*\n?\s*\)", js)
    assert call, 'the drag gesture selector list was not found'

    code = strip_comments(html)
    present = set()
    for attr in re.findall(r'class="([^"]*)"', code):
        present.update(attr.split())

    for selector in call.group(1).split(','):
        cls = selector.strip().lstrip('.')
        assert cls in present, (
            f'the drag gesture arms on {cls!r} but no element carries it, '
            'so that region cannot be dragged'
        )
