"""What `web/sw.js` is allowed to serve from a cache, and what it never is.

The service worker exists here for SPEED, not for offline browsing. Artwork and
the app's own assets are cached hard so a repeat visit paints without waiting on
round trips. The library data is not cached at all, because a stale grid is
indistinguishable from a current one and the app has no way to tell the user
which they are looking at.

Two defects these assertions exist to keep out:

**A cache read that can never succeed.** `/config.json` and `/data/*.json` were
fetched with a `caches.match()` fallback against a cache nothing ever populated.
The line read correctly and had never once returned anything — live code that
cannot succeed, which is worse than no code, because it looks like a working
feature to everyone who reads it.

**An error response answered from cache.** The same function fell back to cache
on any non-OK response, not only a failed fetch. That was inert while the cache
was empty. It would not have stayed inert, and what it would have become is a
mechanism for hiding a container whose entrypoint failed behind the last
response that worked — this project's oldest failure mode, reached from a new
direction. A status is the server speaking; the absence of a status is the
network.

These are source assertions, not behavior tests. Behavior needs a browser; what
is pinned here is the shape the behavior depends on.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / 'web'
SW = WEB / 'sw.js'
INDEX = WEB / 'index.html'

# Anything that reads from a cache. Both spellings: `caches.match` searches every
# cache, `cache.match` searches one that was opened first.
CACHE_READ = re.compile(r'\bcaches?\.match\(')

# Anything that writes to one, including the helper that wraps the write.
CACHE_WRITE = re.compile(r'\b(?:cache\.put|cacheSuccessfulResponse)\(')

# The routes whose freshness is the app's correctness, not its speed.
DATA_ROUTES = ['isConfigRequest', 'isJsonDataRequest']


def strip_js_comments(source: str) -> str:
    """Drop block and line comments, preserving offsets.

    Replaced with spaces rather than removed so every index into the result
    still points at the same character of the original — the assertions below
    report line numbers.

    Stripping is not cosmetic. The comments in `sw.js` quote the defective code
    they describe, braces and all, so brace matching over the raw file walks
    into prose. An assertion that matches an explanatory comment rather than the
    code is a test that cannot fail.
    """

    def blank(match: re.Match) -> str:
        return re.sub(r'\S', ' ', match.group(0))

    source = re.sub(r'/\*.*?\*/', blank, source, flags=re.S)
    source = re.sub(r'//[^\n]*', blank, source)
    return source


def brace_block(source: str, start: int) -> tuple[int, int]:
    """Span of the braced block opening at or after `start`, braces excluded."""
    open_at = source.index('{', start)
    depth = 0
    for index in range(open_at, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return open_at + 1, index
    raise AssertionError('unbalanced braces in sw.js')


def functions(source: str) -> dict[str, tuple[int, int]]:
    """Every top-level function in the file, by name, as a span."""
    found = {}
    for match in re.finditer(r'^(?:async )?function (\w+)\s*\(', source, flags=re.M):
        found[match.group(1)] = brace_block(source, match.end())
    return found


def try_blocks(source: str, span: tuple[int, int]) -> list[tuple[int, int]]:
    """The `try { ... }` bodies inside a span. The network branch of a strategy."""
    start, end = span
    blocks = []
    for match in re.finditer(r'\btry\s*\{', source[start:end]):
        blocks.append(brace_block(source, start + match.start()))
    return blocks


def line_of(source: str, index: int) -> int:
    return source.count('\n', 0, index) + 1


def routed_strategy(source: str, predicate: str) -> str:
    """The strategy the fetch handler hands `predicate`'s requests to."""
    match = re.search(
        re.escape(predicate) + r'\(event\.request\)\)\s*\{\s*event\.respondWith\((\w+)',
        source,
    )
    assert match, f'{predicate} requests are not routed explicitly'
    return match.group(1)


@pytest.fixture(scope='module')
def sw() -> str:
    return strip_js_comments(SW.read_text())


@pytest.fixture(scope='module')
def index() -> str:
    return INDEX.read_text()


# ---------------------------------------------------------------------------
# An error response is never answered from a cache
# ---------------------------------------------------------------------------


def test_no_strategy_answers_a_non_ok_response_from_cache(sw):
    """Pinned by SHAPE, not by function name, because names change.

    The invariant: the network branch of a strategy — everything inside its
    `try` — never consults a cache. A cache read belongs either before the fetch
    (cache-first, stale-while-revalidate, both deliberate) or in the `catch`,
    which is the only place that means *the request never arrived*.

    A `caches.match()` after an `if (response.ok)` inside the try is the defect:
    it turns a 500 from a broken container into a stale 200 from the last time
    it worked, and the user is shown something that looks fine.
    """
    offenders = []
    for name, span in functions(sw).items():
        for block in try_blocks(sw, span):
            for read in CACHE_READ.finditer(sw[block[0] : block[1]]):
                offenders.append(f'{name}() at line {line_of(sw, block[0] + read.start())}')

    assert not offenders, (
        'a cache is read inside the network branch of: '
        + ', '.join(offenders)
        + '. A response the server actually returned must be passed through '
        'whatever its status; only a fetch that THREW may be answered from '
        'cache.'
    )


def test_only_successful_responses_are_cached(sw):
    """A cached error is an error served on every later cache hit.

    Every write site must sit inside an `if (....ok)`. The helper's own
    `cache.put` is exempt and blanked below — it is guarded at each of its call
    sites, which is what this checks.
    """
    declaration = re.search(r'^(?:async )?function cacheSuccessfulResponse\s*\(', sw, flags=re.M)
    assert declaration, (
        'cacheSuccessfulResponse() is gone; this test no longer knows where writes happen'
    )
    # Blank the helper itself — its declaration line as well as its body, since
    # the declaration names the very call pattern being searched for.
    _, end = brace_block(sw, declaration.end())
    start = declaration.start()
    source = sw[:start] + re.sub(r'\S', ' ', sw[start : end + 1]) + sw[end + 1 :]

    guarded = []
    for match in re.finditer(r'if \([^)]*\.ok\)', source):
        guarded.append(brace_block(source, match.end()))

    offenders = [
        line_of(source, write.start())
        for write in CACHE_WRITE.finditer(source)
        if not any(start <= write.start() <= end for start, end in guarded)
    ]
    assert not offenders, (
        f'cache written outside an `.ok` guard at line(s) {offenders}. An error '
        f'response written to the cache becomes the copy every later cache hit '
        f'is served.'
    )


# ---------------------------------------------------------------------------
# The library data is never cached, in either direction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('predicate', DATA_ROUTES)
def test_library_data_is_network_only(sw, predicate):
    """Neither read from a cache nor written to one, and both matter.

    No read, because the app cannot tell the user that what they are looking at
    is out of date — so it does not show them something that might be. An empty
    grid is indistinguishable from a library with no items, and a stale grid is
    indistinguishable from a current one.

    No write, because nothing would read it back, and a cache entry that cannot
    be served is exactly the defect this file used to carry: a `caches.match()`
    fallback against a cache nothing populated, which read correctly and had
    never once returned anything.
    """
    strategy = routed_strategy(sw, predicate)
    body = sw[slice(*functions(sw)[strategy])]

    assert not CACHE_READ.search(body), (
        f'{predicate} is routed to {strategy}(), which reads from a cache. The '
        f'library data must always come from the container or not at all.'
    )
    assert not CACHE_WRITE.search(body), (
        f'{predicate} is routed to {strategy}(), which writes to a cache '
        f'nothing is allowed to read back.'
    )


def test_the_data_routes_are_checked_before_the_cache_first_fallback(sw):
    """Order is the whole protection.

    `/config.json` is not under `/data/` and is not an asset, so without an
    explicit branch above it, the cache-first fallback at the bottom of the
    handler claims it — and a container restart with new settings is never seen
    by an installed client.
    """
    fallback = sw.index('cacheFirstStrategy(event.request)')
    for predicate in DATA_ROUTES:
        assert sw.index(f'{predicate}(event.request)') < fallback, (
            f'{predicate} is checked after the cache-first fallback, which will '
            f'have already claimed those requests'
        )


def test_the_worker_is_not_expected_to_answer_the_configuration(index):
    """A note in the source, because the next person will try.

    The boot read of `config.json` is a synchronous XHR, and a browser
    dispatches no fetch event for one — the worker never sees that request and
    could not answer it from a cache however hard it tried. Measured, not
    assumed. Without this written down, "just cache config.json too" looks like
    a one-line improvement.
    """
    assert 'no fetch event for' in index, (
        'index.html no longer records that a synchronous XHR is invisible to '
        'the service worker; the next person will try to cache config.json'
    )


# ---------------------------------------------------------------------------
# What IS cached, and why it is what makes the app fast
# ---------------------------------------------------------------------------


def test_artwork_is_stale_while_revalidate(sw):
    """The single biggest thing making a repeat visit feel instant.

    The grid paints from cache and revalidates behind it, so thousands of
    posters cost no round trips. Artwork is addressed by a stable path and only
    re-downloaded by the fetchers when its MD5 changes, so the held copy is
    almost always the right one.
    """
    assert routed_strategy(sw, 'isImageDataRequest') == 'staleWhileRevalidateStrategy'
    span = functions(sw)['staleWhileRevalidateStrategy']
    assert CACHE_READ.search(sw[span[0] : span[1]]), (
        'the artwork strategy no longer reads from cache; every poster becomes '
        'a round trip and the grid paints as a field of gaps'
    )


def test_app_assets_share_the_shell_strategy(sw):
    """Network-first with a cache fallback, and NOT cache-first.

    Pairing a network-first shell with cache-first assets is what pinned every
    installed client to the CSS and JS of whichever build it first loaded: the
    markup upgraded, its behaviour did not, and nothing signalled the drift.
    The cache fallback is what keeps the interface painting without waiting on a
    round trip.
    """
    assert routed_strategy(sw, 'isAppAssetRequest') == routed_strategy(sw, 'isAppShellRequest')
    span = functions(sw)[routed_strategy(sw, 'isAppAssetRequest')]
    assert CACHE_WRITE.search(sw[span[0] : span[1]])


def test_static_assets_are_precached(sw):
    """Scoped to the STATIC_ASSETS array.

    `"'/offline.html'" in sw` was the first form of this and it cannot fail: the
    string also occurs in the `caches.match('/offline.html')` further down, so
    deleting the precache entry left it green.
    """
    precache = re.search(r'STATIC_ASSETS = \[(.*?)\]', sw, flags=re.S)
    assert precache, 'STATIC_ASSETS is gone'
    for asset in (
        '/assets/alpine.min.js',
        '/assets/overlays.js',
        '/assets/tokens.css',
        '/assets/overlays.css',
        '/offline.html',
        '/manifest.json',
    ):
        assert f"'{asset}'" in precache.group(1), f'{asset} dropped out of STATIC_ASSETS'


def test_offline_page_is_served_only_as_a_last_resort(sw):
    """It answers for a server that could not be reached, never for one that spoke."""
    served_from = []
    for name, span in functions(sw).items():
        body = sw[span[0] : span[1]]
        if "caches.match('/offline.html')" not in body:
            continue
        catch_at = body.find('catch')
        assert catch_at != -1 and body.index("caches.match('/offline.html')") > catch_at, (
            f'{name}() serves the offline page outside its catch block; it is a '
            f'last resort for an unreachable server, not a response to one'
        )
        served_from.append(name)

    assert served_from, 'nothing serves /offline.html; an offline navigation gets a blank screen'


# ---------------------------------------------------------------------------
# The 5xx page
#
# `error_page 500 502 503 504 /50x.html` pointed at `/usr/share/nginx/html`,
# which ships only the distro's own index. So `/50x.html` did not exist, the
# 5xx fell through to `error_page 404 /index.html`, and nginx served the whole
# application shell with status 404 — measured at 186,727 bytes. A user whose
# backend had failed got a working-looking app that could not load its data,
# which is indistinguishable from a library with no media in it.
#
# The status a user sees has to be the status that occurred.
# ---------------------------------------------------------------------------

NGINX_CONF = REPO_ROOT / 'config' / 'nginx.conf'


def test_the_5xx_page_exists_where_nginx_looks_for_it():
    """The directive and the file are a PAIR. Either alone is worse than neither."""
    conf = NGINX_CONF.read_text()
    assert 'error_page 500 502 503 504 /50x.html;' in conf, (
        'nginx no longer maps 5xx to an error page'
    )

    block = re.search(r'location = /50x\.html \{(.*?)\}', conf, flags=re.S)
    assert block, 'the /50x.html location is gone, so the error_page has nowhere to go'
    assert 'root /app/web' in block.group(1), (
        'the 5xx page is rooted outside /app/web, where the repo does not put '
        'it — it pointed at the distro web root once, and every 5xx became a '
        '404 serving the whole app shell'
    )
    assert (WEB / '50x.html').exists(), (
        'config/nginx.conf promises /50x.html and web/ does not contain it; a '
        '5xx will fall through to error_page 404 and serve the application'
    )


def test_the_5xx_page_is_internal():
    """Otherwise it is a URL anyone can fetch and get a 200 error page from."""
    block = re.search(r'location = /50x\.html \{(.*?)\}', NGINX_CONF.read_text(), flags=re.S)
    assert block and 'internal;' in block.group(1), (
        'the 5xx page is directly requestable, so it can report an error that is not happening'
    )


def test_the_5xx_page_depends_on_nothing_it_may_not_get():
    """It renders when something is already broken, so it cannot need /assets/.

    Comments stripped first. The page's own comment explains why it must not
    reference `/assets/`, and that prose contains the string — so the unstripped
    assertion judged the note about the rule instead of the rule. The same trap
    `test_tray_presentation` records for `aria-live`.
    """
    page = re.sub(r'<!--.*?-->', '', (WEB / '50x.html').read_text(), flags=re.S)
    assert 'rel="stylesheet"' not in page, (
        'the 5xx page links a stylesheet; if nginx is failing it may not be served'
    )
    for external in ('/assets/', 'http://', 'https://'):
        assert external not in page, (
            f'the 5xx page references {external}, which it cannot rely on reaching'
        )


def test_the_5xx_page_is_not_precached(sw):
    """A cached copy would answer for a server that never spoke.

    The rule the whole cache policy turns on: a response the server actually
    returned is never replaced by a cached one, and a 5xx IS the server
    speaking.
    """
    assert "'/50x.html'" not in sw, (
        'the 5xx page is in the service worker; it must be served by nginx with '
        'the real status, never handed back from a cache'
    )
