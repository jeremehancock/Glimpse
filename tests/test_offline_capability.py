"""Guarantees for `serve-the-library-offline`.

Two defects, and the second is the dangerous one.

The app had every marker of an offline-capable PWA and no offline capability:
`config.json` and the library snapshots were fetched with a cache fallback that
nothing ever populated. The fallback line existed, read correctly, and could not
succeed — which is why nobody noticed there was no offline support to begin with.

The second is that the same function fell back to cache on **any non-OK
response**, not only on a failed fetch. That was inert while the cache was empty.
Filling the cache — which is the whole of this change — turns it into a
mechanism for hiding a container whose entrypoint failed behind the last
configuration that worked. That is this project's oldest failure mode reached
from a new direction, and it is why the split between *unreachable* and
*answered badly* is pinned by shape below rather than by function name.

These are source assertions, not behavior tests. Offline behavior needs a real
browser with its network disabled; what is pinned here is the shape it rests on.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / 'web'
SW = WEB / 'sw.js'
INDEX = WEB / 'index.html'
OFFLINE = WEB / 'offline.html'

# Anything that reads from a cache. Both spellings: `caches.match` searches every
# cache, `cache.match` searches one that was opened first.
CACHE_READ = re.compile(r'\bcaches?\.match\(')

# Anything that writes to one, including the helper that wraps the write.
CACHE_WRITE = re.compile(r'\b(?:cache\.put|cacheForOfflineUse)\(')


def strip_js_comments(source: str) -> str:
    """Drop block and line comments, preserving offsets.

    Replaced with spaces rather than removed so every index into the result
    still points at the same character of the original — the assertions below
    report line numbers.

    Stripping is not cosmetic here. The comments in `sw.js` quote the defective
    code they describe, braces and all, so brace matching over the raw file
    walks into prose. An assertion that matches an explanatory comment rather
    than the code is a test that cannot fail.
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


@pytest.fixture(scope='module')
def sw() -> str:
    return strip_js_comments(SW.read_text())


@pytest.fixture(scope='module')
def index() -> str:
    return INDEX.read_text()


# ---------------------------------------------------------------------------
# A cached copy answers for a server that could not be reached, never for one
# that spoke.
# ---------------------------------------------------------------------------


def test_no_strategy_answers_a_non_ok_response_from_cache(sw):
    """Pinned by SHAPE, not by function name, because the name will change.

    The invariant is that the network branch of a strategy — everything inside
    its `try` — never consults a cache. A cache read belongs either before the
    fetch (cache-first, stale-while-revalidate, both deliberate) or in the
    `catch`, which is the only place that means *the request never arrived*.

    A `caches.match()` after an `if (response.ok)` inside the try is precisely
    the defect: it turns a 500 from a broken container into a stale 200 from the
    last time it worked, and the user is shown a library that looks fine.
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
        'cache. A status is the server speaking, the absence of a status is '
        'the network.'
    )


def test_a_cache_is_still_read_when_the_fetch_throws(sw):
    """The other half of the same rule, or the test above passes by deleting it.

    Removing every cache read would satisfy the invariant and remove the offline
    support this change exists to add.
    """
    strategy = functions(sw)['networkOnlyWithOfflineFallback']
    body = sw[strategy[0] : strategy[1]]
    catch_at = body.index('catch')
    assert CACHE_READ.search(body[catch_at:]), (
        'the unreachable branch does not read from cache; there is no offline fallback at all'
    )


# ---------------------------------------------------------------------------
# What the app needs to start is cached
# ---------------------------------------------------------------------------


def routed_strategy(source: str, predicate: str) -> str:
    """The strategy the fetch handler hands `predicate`'s requests to."""
    match = re.search(
        re.escape(predicate) + r'\(event\.request\)\)\s*\{\s*event\.respondWith\((\w+)',
        source,
    )
    assert match, f'{predicate} requests are not routed explicitly'
    return match.group(1)


def test_the_snapshots_are_written_to_a_cache(sw):
    """Precaching the shell was never enough and never could be.

    It gets the app as far as reading its configuration and then rendering
    nothing — and an empty grid is indistinguishable from a library with no
    items, which this project already treats as a defect. The snapshots are what
    make an offline start worth having.
    """
    strategy = routed_strategy(sw, 'isJsonDataRequest')
    span = functions(sw)[strategy]
    assert CACHE_WRITE.search(sw[span[0] : span[1]]), (
        f'the snapshots are routed to {strategy}(), which never writes to a '
        f'cache. Its offline fallback can therefore never return anything — the '
        f'exact defect this change closed, restored.'
    )


def test_the_worker_neither_caches_nor_answers_the_configuration(sw):
    """The worker cannot see the boot read, so it must not pretend to.

    The configuration is read by a synchronous XHR, and a browser dispatches no
    fetch event for one. The worker therefore never receives that request: a
    cache entry written here could not be served to the only caller that
    matters, and an offline fallback here could never fire.

    Both absences are load-bearing. Live code that cannot succeed is precisely
    the defect this change removed — the original fallback read correctly and
    had never once returned anything — so reintroducing it on this route would
    be the same lie in a new place. Retention lives in the page, in
    localStorage, which is the only same-origin store readable before first
    paint.

    The route still has to exist: without it config.json falls through to the
    cache-first branch at the bottom of the handler, and a container restart
    with new settings is never seen.
    """
    strategy = routed_strategy(sw, 'isConfigRequest')
    span = functions(sw)[strategy]
    body = sw[span[0] : span[1]]
    assert not CACHE_WRITE.search(body), (
        f'{strategy}() writes the configuration to a cache that nothing can '
        f'read it back from — the boot read is a synchronous XHR the worker '
        f'never sees'
    )
    assert not CACHE_READ.search(body), (
        f'{strategy}() reads a cache it can never fill; that fallback cannot '
        f'fire and reads as offline support that does not exist'
    )
    assert strategy != routed_strategy(sw, 'isJsonDataRequest'), (
        'the configuration and the snapshots share a strategy again. They are '
        'retained by different mechanisms because only one of the two reads is '
        'visible to the worker.'
    )


def test_the_configuration_route_is_checked_before_the_cache_first_fallback(sw):
    """Its whole purpose. config.json is not under /data/ and not an asset."""
    config_route = sw.index('isConfigRequest(event.request)')
    fallback = sw.index('cacheFirstStrategy(event.request)')
    assert config_route < fallback


def test_only_successful_responses_are_cached(sw):
    """A cached error is an error served forever, on every offline start.

    Every write site must sit inside an `if (....ok)`. The helper's own
    `cache.put` is exempt and blanked below — it is guarded at each of its call
    sites, which is what this checks.
    """
    declaration = re.search(r'^(?:async )?function cacheForOfflineUse\s*\(', sw, flags=re.M)
    assert declaration, (
        'cacheForOfflineUse() is gone; this test no longer knows where writes happen'
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
        f'response written to the cache becomes the copy every later offline '
        f'start is served.'
    )


def test_artwork_is_still_stale_while_revalidate(sw):
    """This is why an offline start is worth having.

    A cached snapshot renders with its posters instead of as a grid of gaps.
    Artwork is addressed by a stable path and only re-downloaded when its MD5
    changes, so the held copy is the right thing to serve.
    """
    assert routed_strategy(sw, 'isImageDataRequest') == 'staleWhileRevalidateStrategy'
    span = functions(sw)['staleWhileRevalidateStrategy']
    assert CACHE_READ.search(sw[span[0] : span[1]])


# ---------------------------------------------------------------------------
# The offline page, which is now hard to reach by accident
# ---------------------------------------------------------------------------


def test_offline_page_is_precached_and_served_as_the_last_resort(sw):
    """It only appears for a client that has never successfully loaded.

    That makes it the part of this file nothing exercises, which is exactly how
    the copy that used to be inlined in `sw.js` went stale and started showing
    Plex orange to Jellyfin installs.
    """
    # Scoped to the STATIC_ASSETS array. `"'/offline.html'" in sw` was the first
    # form of this assertion and it cannot fail: the string also occurs in the
    # `caches.match('/offline.html')` this same test requires, so deleting the
    # precache entry left it passing.
    precache = re.search(r'STATIC_ASSETS = \[(.*?)\]', sw, flags=re.S)
    assert precache, 'STATIC_ASSETS is gone'
    assert "'/offline.html'" in precache.group(1), (
        '/offline.html dropped out of STATIC_ASSETS; nothing puts it in the '
        'cache the catch block below expects to find it in'
    )

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

    assert served_from, 'nothing serves /offline.html; a first offline load gets a blank screen'


def test_offline_page_no_longer_claims_the_app_needs_a_connection():
    """Its copy has to match the one case that still reaches it.

    Since this change a device that has loaded once browses its saved library
    offline and never sees this page. Only a device that has never loaded does,
    and telling that user "Glimpse needs a connection" is both wrong and useless.
    """
    body = re.sub(r'<!--.*?-->', '', OFFLINE.read_text(), flags=re.S)
    assert 'needs a connection' not in body, (
        'the offline page still says the app needs a connection; it now only '
        'appears for a device with nothing cached to fall back on'
    )
    assert 'offline' in body.lower()


# ---------------------------------------------------------------------------
# The app says when it is running on saved data
# ---------------------------------------------------------------------------


def test_the_page_can_tell_a_cached_response_apart(sw, index):
    """The one channel that carries the fact, so both ends must agree on it.

    A cached response is otherwise indistinguishable from a live one by the time
    the app sees it.
    """
    assert 'X-Glimpse-From-Cache' in sw, 'the worker does not mark cached responses'

    # Named explicitly. Asserting the header string appears somewhere in
    # index.html cannot fail — it is declared as a constant there, so gutting
    # the read left the name behind and the test green.
    assert 'headers.get(FROM_CACHE_HEADER)' in index, (
        'the snapshot fetches do not check the cached-response marker, so the '
        'app cannot tell a cached grid from a live one'
    )


# ---------------------------------------------------------------------------
# The configuration is retained by the page, because the worker cannot see it
# ---------------------------------------------------------------------------


def boot_script(index: str) -> str:
    """The parser-blocking block that reads config.json before first paint."""
    start = index.index('window.GLIMPSE = (function () {')
    return index[start : index.index('</script>', start)]


def test_the_configuration_is_retained_where_a_boot_read_can_reach_it(index):
    """localStorage, and it has to be localStorage.

    Everything read before first paint must be synchronous — the theme is on
    <html> before anything paints, or two thirds of users see a flash of the
    wrong brand on every load. The Cache API is not synchronous, and the worker
    is not even consulted for a synchronous XHR. That leaves exactly one store.
    """
    boot = boot_script(index)
    assert 'localStorage' in boot, (
        'nothing retains the configuration in the boot script; an unreachable '
        'container means the configuration error page, which is the whole '
        'defect this change exists to close'
    )
    assert 'JSON.parse(window.localStorage.getItem' in boot, 'the retained copy is never read back'
    assert 'window.localStorage.setItem' in boot, 'the retained copy is never written'


def test_a_container_that_answers_is_believed_over_the_retained_copy(index):
    """The boundary of the exception, pinned in the code that draws it.

    `answered` must come from the try/catch boundary and nothing else: send()
    throws only when the request could not be delivered. Reading the retained
    copy on any other condition — a status test, a truthiness check on the body
    — is what turns this from offline support into a mechanism for hiding a
    container whose entrypoint failed.
    """
    boot = boot_script(index)
    assert re.search(r'answered\s*=\s*true;', boot), (
        'nothing records that the container answered; the retained copy cannot '
        'be correctly excluded'
    )
    recall = re.search(r'\}\s*else if \(!answered\) \{\s*config = recall\(\);', boot)
    assert recall, (
        'the retained configuration is not gated on `else if (!answered)`. It '
        'must be reachable ONLY when the request never arrived — not on a '
        'non-2xx status, and not on a body that would not parse.'
    )


def test_only_a_configuration_the_container_returned_is_retained(index):
    """Never a default, never an error, never an unparsed body.

    A retained copy is a fact about this container recorded from its own answer.
    Storing anything else makes it a guess, and a guess is the failure the
    "never defaulted around" rule exists to prevent.
    """
    boot = boot_script(index)
    stored = re.search(r'if \(config\) \{\s*remember\(body\);', boot)
    assert stored, (
        'the configuration is retained outside the `if (config)` guard, so an '
        'error body or an unparsed one could be stored and then served to every '
        'later offline start'
    )


def test_the_offline_indicator_is_announced_and_not_colour_alone(index):
    """A dot is not a message.

    `role="status"` announces it when it appears, and the text is what carries
    the meaning — a user who cannot distinguish the colour still gets told.
    """
    badge = re.search(r'<p class="offline-badge".*?</p>', index, flags=re.S)
    assert badge, 'the offline indicator is not in the markup'
    markup = badge.group(0)
    assert 'role="status"' in markup, 'the indicator is not announced to assistive technology'
    assert 'hidden' in markup, 'the indicator must default to hidden'
    assert 'Offline' in markup, 'the indicator carries no text'
    assert 'aria-hidden="true"' in markup, 'the decorative dot is not hidden from screen readers'


def test_the_indicator_reports_current_state_not_a_boot_flag(index):
    """It has to clear when the server is reached again.

    A flag set once at boot would leave the app claiming to be offline for the
    rest of the session, which is the same failure as never saying so at all —
    the user cannot trust what it says either way.
    """
    assert "addEventListener('online'" in index, (
        'nothing reacts to the network returning; the indicator would be stuck '
        'from boot until reload'
    )
    assert 'setOfflineIndicator(' in index
    assert 'servedFromCache(moviesResponse)' in index, (
        'the indicator is not set from the snapshot responses, so reaching the '
        'server again cannot clear it'
    )
