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
