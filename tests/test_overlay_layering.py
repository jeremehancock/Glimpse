"""Guarantees for the four defects `fix-overlay-layering-and-dead-tray-controls`
closed. Every one of them looked correct in a browser.

The layering fault rendered a dialog underneath the header on a desktop and left
the header lit above every tray's backdrop on a phone — visible, but only if you
knew an overlay was supposed to cover it. The binding fault produced controls
that highlighted, dismissed their tray, and did nothing, with no error anywhere.
The caching fault presented as a fixed bug still being broken. And the artwork
covered the one affordance that dismisses a tray, legibly or not depending on
which item happened to be open.

These are source assertions, not behavior tests. Behavior needs a browser; what
is pinned here is the shape the behavior depends on.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / 'web'
INDEX = WEB / 'index.html'
TOKENS = WEB / 'assets' / 'tokens.css'
OVERLAYS_CSS = WEB / 'assets' / 'overlays.css'
OVERLAYS_JS = WEB / 'assets' / 'overlays.js'
SW = WEB / 'sw.js'
NGINX = REPO_ROOT / 'config' / 'nginx.conf'


def block_after(source: str, opener: str) -> str:
    """The body of the rule or function introduced by `opener`.

    Terminated on a line that is exactly eight spaces and a closing brace — the
    indentation every top-level rule and function inside index.html's inline
    <style> and <script> closes at.

    Not `\\n\\s{8}\\}`, which is what this was first written as and is quietly
    wrong: `\\s` matches newlines, so eight of them satisfy the count and the
    non-greedy capture ends in the middle of the block. Both assertions built on
    it passed against source with the defect reintroduced — a test that cannot
    fail, which is the one thing these must never be.
    """
    match = re.search(
        re.escape(opener) + r'(.*?)^ {8}\}',
        source,
        flags=re.S | re.M,
    )
    assert match, f'no block found for {opener!r}'
    return match.group(1)


def strip_comments(source: str) -> str:
    """Drop HTML and block comments.

    The comments here describe the values that were wrong, by name and number.
    Asserting against prose would fail the very tests that guard the fix.
    """
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return source


@pytest.fixture(scope='module')
def index() -> str:
    return strip_comments(INDEX.read_text())


@pytest.fixture(scope='module')
def tokens() -> str:
    return strip_comments(TOKENS.read_text())


@pytest.fixture(scope='module')
def sw() -> str:
    return SW.read_text()


@pytest.fixture(scope='module')
def nginx() -> str:
    return NGINX.read_text()


# ---------------------------------------------------------------------------
# Layering
#
# The ladder is TRANSCRIBED here rather than parsed out of tokens.css. A test
# that recomputes the ordering from the same file it is checking agrees with
# whatever that file says and can never fail — which is the one thing this must
# not do. If these numbers change, changing them here is the point at which
# someone states that they meant to.
# ---------------------------------------------------------------------------

Z_CHROME = 30
Z_SHEET = 50
Z_MODAL = 55

# Every fixed-position element of the page's own chrome. Not a list of things
# that happen to have a z-index — a value that only orders siblings inside a
# positioned ancestor (`.modal-header`, `.trailer-loading`, `.search-clear`)
# never competes with an overlay and is not this test's business.
#
# `.swipe-indicator` was here until the tab drag replaced it. It was a toast
# announcing which tab a committed swipe had landed on, and a first-load tip
# teaching the gesture; a drag that follows the thumb and springs back is both
# of those, delivered by being used.
CHROME_SELECTORS = ('.header', '.scroll-to-top')


def test_layering_tokens_hold_their_order(tokens):
    """Chrome below trays below dialogs.

    A dialog must outrank a tray because a dialog can be raised from inside one
    — the trailer opens from the detail overlay — and a dialog rendered behind
    the tray that raised it cannot be used.
    """
    for name, expected in (
        ('--z-chrome', Z_CHROME),
        ('--z-sheet', Z_SHEET),
        ('--z-modal', Z_MODAL),
    ):
        match = re.search(rf'{name}:\s*(\d+)', tokens)
        assert match, f'{name} is not declared in tokens.css'
        assert int(match.group(1)) == expected, (
            f'{name} is {match.group(1)}, expected {expected}. If the ladder '
            f'moved on purpose, update this test deliberately.'
        )
    assert Z_CHROME < Z_SHEET < Z_MODAL


@pytest.mark.parametrize('selector', CHROME_SELECTORS)
def test_page_chrome_uses_the_chrome_token(index, selector):
    """Chrome reads the token; it does not restate a number.

    `.header` was 100 and `.scroll-to-top` was 1000 — both above both overlay
    tiers, and neither chosen against a scale. A literal here is how the next
    one gets picked by looking at its neighbours.
    """
    block = re.search(rf'\n\s*{re.escape(selector)}\s*\{{(.*?)\}}', index, flags=re.S)
    assert block, f'{selector} has no rule in index.html'
    body = block.group(1)
    assert 'z-index' in body, f'{selector} declares no z-index'
    assert 'var(--z-chrome)' in body, (
        f'{selector} does not read --z-chrome. Page chrome must rank below '
        f'every overlay, or an open overlay does not cover it.'
    )


def test_no_page_chrome_outranks_the_overlay_scale(index):
    """No literal anywhere in the page reaches the overlay tiers.

    Catches a chrome element this test does not know about by name.
    """
    offenders = [
        int(value) for value in re.findall(r'z-index:\s*(\d+)\s*;', index) if int(value) >= Z_SHEET
    ]
    assert not offenders, (
        f'literal z-index values at or above the tray tier ({Z_SHEET}): '
        f'{sorted(set(offenders))}. An overlay cannot cover these.'
    )


def test_overlays_read_their_tiers_from_tokens():
    css = strip_comments(OVERLAYS_CSS.read_text())
    assert 'z-index: var(--z-sheet)' in css
    assert 'z-index: var(--z-modal)' in css


# ---------------------------------------------------------------------------
# Bindings inside the teleported tray
# ---------------------------------------------------------------------------


def test_actions_tray_is_still_teleported(index):
    """The premise of every assertion below.

    If the tray stops being teleported these tests still pass but stop meaning
    anything, so the premise is pinned too. It is teleported because
    `backdrop-filter` on the header makes it a containing block for fixed
    descendants — see the note on the markup.
    """
    assert 'x-teleport="body"' in index


def test_relocated_controls_are_bound_after_alpine_initialises(index):
    """The binding pass must run after the teleport has happened.

    A parse-time pass finds only the header's copies: the tray is still inert
    `<template>` content, which querySelectorAll does not reach, and Alpine is a
    `defer` script that has not run yet. Every control in that tray was left
    with no handler, and nothing anywhere threw.
    """
    assert "addEventListener('alpine:initialized'" in index, (
        'nothing is bound on alpine:initialized; controls inside the teleported '
        'Actions tray will have no handlers'
    )
    body = block_after(index, 'function bindRelocatedControls() {')
    assert 'bindSortButtons()' in body
    assert 'renderServerSwitcher()' in body


def test_binding_passes_are_idempotent(index):
    """They run twice by design, so binding must replace rather than accumulate.

    `onclick =` assignment replaces; addEventListener stacks. The earlier calls
    are deliberately left in place so the header still works if Alpine ever
    fails to load, which means both passes run twice on every normal boot.
    """
    body = block_after(index, 'function bindSortButtons() {')
    assert 'button.onclick' in body, (
        'sort buttons must be bound by assignment, not addEventListener — the '
        'pass runs more than once'
    )
    assert 'addEventListener' not in body


def test_scroll_from_inside_an_overlay_goes_through_the_overlay_system(index):
    """A direct scrollTo cannot work from inside a tray.

    The scroll lock pins the body, so scrollTo moves nothing, and the lock then
    restores the position captured when the overlay opened — overwriting it. The
    grid re-sorted correctly and the page slid back to where the user had been.
    """
    for opener in (
        'function bindSortButtons() {',
        'function genreItem(value, label, count) {',
        'function switchTab(contentName, direction) {',
        # The animated tab path scrolls to the top of the incoming tab too, and
        # does it while an overlay may still be closing, so it is bound by this
        # exactly as the instant path is. Both of its scrolls live in the shared
        # setup and the shared teardown rather than in `switchTabAnimated()`:
        # the drag and the slide from rest use one freeze, and an abandoned drag
        # scrolls BACK from that teardown.
        'function beginTabTransition(contentName, outgoing, incoming, lifted) {',
        'function endTabTransition() {',
    ):
        body = block_after(index, opener)
        assert 'window.scrollTo(' not in body, (
            f'{opener} scrolls the window directly; from inside an overlay the '
            f'body is pinned, so that moves nothing and is then overwritten by '
            f'the scroll lock restoring the old position'
        )
        assert 'GlimpseOverlays.scrollPageTo' in body, (
            f'{opener} does not route its scroll through the overlay system'
        )


def test_overlays_expose_the_scroll_helper():
    js = OVERLAYS_JS.read_text()
    assert 'scrollPageTo' in js
    assert 'window.GlimpseOverlays' in js


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_app_assets_are_not_cache_first(sw):
    """The shell was network-first while the assets it loads were cache-first.

    So the markup upgraded and its behaviour did not — permanently, since the
    cache name never changed. This is the pairing that made a fixed bug look
    broken.
    """
    assert 'function isAppAssetRequest' in sw
    handler = sw.split('addEventListener', 1)[1]
    asset_branch = re.search(
        r'isAppAssetRequest\(event\.request\)\)\s*\{\s*event\.respondWith\((\w+)',
        handler,
    )
    assert asset_branch, '/assets/ requests are not routed explicitly'
    assert asset_branch.group(1) == 'networkFirstWithCacheFallback', (
        f'/assets/ routed through {asset_branch.group(1)}; it must use the same '
        f'strategy as the app shell that loads it'
    )


def test_asset_route_is_checked_before_the_cache_first_fallback(sw):
    """Order matters: the fallback at the end is still cache-first."""
    asset_route = sw.index('isAppAssetRequest(event.request)')
    fallback = sw.index('cacheFirstStrategy(event.request)')
    assert asset_route < fallback


def test_static_assets_are_still_precached(sw):
    """Offline capability rests on these, Alpine most of all.

    It is vendored rather than fetched from a CDN precisely so the app survives
    the network failing, and that only holds while it is precached.
    """
    for asset in (
        '/assets/alpine.min.js',
        '/assets/overlays.js',
        '/assets/tokens.css',
        '/assets/overlays.css',
        '/offline.html',
        '/manifest.json',
    ):
        assert f"'{asset}'" in sw, f'{asset} dropped out of STATIC_ASSETS'


def test_network_fetches_bypass_the_http_cache(sw):
    """Correcting the header cannot retract an entry already handed out.

    A client holding a `max-age=604800` entry from before the fix would serve it
    for up to a week. Bypassing the HTTP cache is what heals it on next load.
    """
    assert "cache: 'reload'" in sw, (
        "networkFirstWithCacheFallback must fetch with cache: 'reload'; a plain "
        'fetch is satisfied by the browser HTTP cache'
    )
    assert 'new Request(url, { cache: ' in sw, (
        'the install precache must also bypass the HTTP cache, or the new worker '
        'faithfully precaches the previous build'
    )


def test_cache_name_was_bumped(sw):
    """The strategy fix cannot clean up entries already poisoned; this does."""
    match = re.search(r"CACHE_NAME = 'glimpse-media-viewer-v([\d.]+)'", sw)
    assert match, 'CACHE_NAME not found'
    assert match.group(1) != '8.1', 'CACHE_NAME still v8.1; poisoned entries survive'


# ---------------------------------------------------------------------------
# nginx cache headers
# ---------------------------------------------------------------------------


def test_service_worker_is_always_revalidated(nginx):
    """The worst thing in the file to cache.

    It is the code that decides what everything else may serve, so a held copy
    freezes the caching policy of the whole app — and withholds the upgrade that
    would fix it. It was matched by the `.js` extension rule and given 7 days.
    """
    block = re.search(r'location = /sw\.js \{(.*?)\}', nginx, flags=re.S)
    assert block, '/sw.js has no exact-match location; the .js regex will claim it'
    assert 'no-cache' in block.group(1)


def test_app_assets_are_revalidated(nginx):
    """Unversioned filenames cannot be held.

    Nothing under web/ is built or bundled, so a changed file keeps its URL. The
    service worker's network-first fetch consults this cache, so a long max-age
    here defeats it — and neither layer looks wrong on its own.
    """
    block = re.search(r'location \^~ /assets/ \{(.*?)\}', nginx, flags=re.S)
    assert block, '/assets/ has no ^~ location; the extension regex will claim it'
    assert 'no-cache' in block.group(1)


def test_genuinely_static_files_keep_their_long_cache(nginx):
    """Not an argument against caching — an argument about which files."""
    block = re.search(r'location ~\* \^/images/.*?\{(.*?)\}', nginx, flags=re.S)
    assert block, '/images/ location missing'
    assert 'max-age=604800' in block.group(1)


# ---------------------------------------------------------------------------
# The grab handle over artwork
# ---------------------------------------------------------------------------


def test_grip_is_lifted_above_the_artwork(index):
    """Paint order, not opacity.

    `.modal-backdrop-art` is positioned and the grip is not, so the artwork
    covers it whatever the mask says. The mask alone loses to paint order; the
    lift alone leaves a grey handle on an arbitrary photograph.
    """
    block = re.search(r'\.modal__fixed \.sheet__grip\s*\{(.*?)\}', index, flags=re.S)
    assert block, '.modal__fixed .sheet__grip has no rule'
    assert 'position: relative' in block.group(1)
    assert 'z-index: 1' in block.group(1)


def test_artwork_clears_past_the_handle_not_up_to_it(index, tokens):
    """The fade must END beyond the handle, not arrive at opaque on its edge.

    `--grip-height` is the handle's LOWER edge. A gradient running
    `transparent 0 -> opaque var(--grip-height)` therefore covers the handle
    itself, which sits in the last 5px of that distance at 71-100% opacity.
    Clearing a region means being clear across the whole of it and then some.
    """
    assert '--grip-clear' in tokens, '--grip-clear is not declared'
    derived = re.search(r'--grip-clear:\s*calc\(var\(--grip-height\)([^)]*)\)', tokens)
    assert derived, (
        '--grip-clear must be derived from --grip-height, not restated. Two '
        'hand-copied values drift, and the symptom is an illegible handle on '
        'bright artwork only.'
    )
    assert '+' in derived.group(1), '--grip-clear must be LARGER than --grip-height'

    body = block_after(index, '.modal-backdrop-art {')
    # Both declarations, not just whichever comes first: the prefixed and
    # unprefixed properties are two separate gradients that have to agree, and
    # an edit to one of them is exactly how they stop agreeing.
    declarations = re.findall(r'(?:-webkit-)?mask-image:\s*(.*?);', body, flags=re.S)
    assert len(declarations) == 2, (
        f'expected a prefixed and an unprefixed mask-image, found {len(declarations)}'
    )
    for gradient in declarations:
        assert 'transparent var(--grip-clear)' in gradient, (
            'the mask must hold transparent all the way to --grip-clear before '
            "it begins to fade, not arrive at opaque on the handle's edge"
        )
        assert 'var(--grip-height)' in gradient
