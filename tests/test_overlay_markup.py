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
