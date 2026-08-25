## Decision 0 — this change reversed direction, and why that is recorded here

It began as `serve-the-library-offline`. The app had every marker of an
offline-capable PWA and no offline capability, so the change made it real:
snapshots cached, configuration retained in `localStorage`, a header indicator
whenever the data was not live. That was built and **verified 30/30 in a real
browser** — offline start, artwork, search, sorting, genre filter, a true 500, a
malformed body, recovery, the indicator clearing without a reload.

Then the user tested it and said: *"I don't really want the cached version to
display when the container is stopped. I mainly just want to be sure that the
images and UI load quickly using cache."*

That is not a small correction, it is a different goal, and it was the right one.
The punch-list item read "verify the PWA caches properly" — a question about
**speed**. An earlier session had read it as "make the app work offline" and
built a capability nobody asked for. Showing a library that may be out of date is
the same ambiguity this app refuses everywhere else; the objection was sound.

So the offline capability was withdrawn and what remains is the part that was
always worth doing: delete the dead cache fallback, fix the dangerous one, keep
and pin the caching that actually makes the app fast.

**The reverted work is not wasted and should not be re-derived.** Two findings
from it are load-bearing and are recorded in `CLAUDE.md`:

- A browser dispatches **no fetch event for a synchronous XHR**. The boot read of
  `config.json` is one, so the service worker never sees that request and cannot
  cache or answer it. Anyone who tries to "just cache config.json" will spend a
  session finding this out.
- The container's nginx declares `error_page 500 502 503 504 /50x.html` and ships
  no `50x.html`, so every 5xx it generates is rewritten to a 404. Out of scope
  here; worth knowing.

## Context

The service worker carried two pieces of live code that could not succeed.

```
/config.json      alwaysFreshStrategy  ->  fetch(no-store), then caches.match()
/data/*.json      alwaysFreshStrategy  ->  same
                                              ^
                        nothing ever wrote either one to a cache,
                        so this fallback had never returned anything
```

Both looked like offline support. That is why nobody noticed there wasn't any,
and it is the reason to delete such code rather than leave it: a reader cannot
tell a feature from its shell.

A second problem sat in the same function and was the more dangerous one. It fell
back to cache on **any non-OK response**, not only on a failed fetch:

```js
if (response.ok) { return response; }
const cachedResponse = await caches.match(request);
return cachedResponse || response;          // <- a 500 becomes a stale 200
```

Inert only because the cache was always empty. Fill it — which the withdrawn
version did — and it becomes a mechanism for hiding a broken entrypoint behind
the last response that worked.

## Goals / Non-Goals

**Goals:**

- A repeat visit paints its grid without requesting a single poster.
- The interface renders from cache and still upgrades when the app does.
- The library data is always the container's current answer, or an error.
- A server that answers is always believed, whatever it says.
- Tests that fail if any of the above is quietly undone.

**Non-Goals:**

- Offline browsing. Explicitly withdrawn — see decision 0.
- Retaining the configuration anywhere. Same.
- An indicator for stale data. There is no stale data to indicate.
- Caching artwork *more* aggressively. Stale-while-revalidate is already right
  for a path that only changes when its content does.
- Any change to what the fetchers write or how often.

## Decisions

### 1. Split "could not reach" from "answered badly"

One `try`/`catch` boundary already separates them and the old code crossed it. A
thrown fetch is unreachable; a returned response — 200, 404, 500 — is an answer.

```
fetch() throws              ->  unreachable  ->  a cache MAY answer
fetch() returns, !ok        ->  answered     ->  return it, cache stays out
fetch() returns, ok         ->  answered     ->  return it, cache it if cacheable
```

**Alternative considered:** treat 5xx as unreachable and 4xx as answered.
Rejected — a 500 from the container is precisely the "entrypoint failed" case the
user must see.

**Known limitation, accepted.** Behind a reverse proxy this does not hold: a
stopped container makes the proxy answer `502`/`504`, which is the *network*
failing reported as a status. Nothing downstream can tell that apart from the
container itself returning 502. It does not matter here — the data routes never
consult a cache anyway, so the outcome is the same error page either way. It
would matter to anyone who reintroduces offline support, which is why it is
written down.

### 2. The data is not cached at all, rather than cached and unused

Deleting the read without deleting the write would leave entries nothing can
serve — the same "live code that cannot succeed" shape, just inverted. Both go.

### 3. Artwork is the exception, and it is the whole performance story

Posters are cached hard and served before revalidating. That is what makes the
grid instant, and it costs nothing in correctness: the fetchers rewrite a poster
only when its MD5 changes, so a held copy is almost always the current one.

Measured against a 400-item library, third load, reading the container's own
nginx access log rather than the timing API:

| | Requests reaching the container |
| --- | --- |
| Posters | **0** (15 rendered) |
| Snapshots | 2 |
| `config.json` | 1 |
| CSS / JS | 4 (revalidated, 106 ms total) |

`PerformanceResourceTiming.transferSize` is **not** usable for this: it reads 0
for anything a service worker handled, whether the worker went to the network or
not. Measuring that way reported the snapshots as cache hits when they were not.
The access log is the only witness that cannot be fooled.

## Risks / Trade-offs

- **The app is unusable with the container down.** By choice. The alternative was
  built and withdrawn.
- **Every load costs a snapshot fetch.** For a few thousand items that is a small
  JSON document over a LAN, and it is what keeps the grid honest. Artwork, which
  actually dominates, costs nothing.
- **The offline page is now nearly unreachable** — only an installed worker, no
  network, and an uncached route reaches it. It will rot the way the copy inlined
  in `sw.js` did if nothing exercises it.

## Migration Plan

No data migration, no configuration change, no compose change. An ordinary image
rebuild. `CACHE_NAME` and `DYNAMIC_CACHE` are bumped to `v8.3`, which evicts the
snapshot entries written by the withdrawn version — otherwise a client that ran
it would hold library JSON that nothing will ever read.

## Open Questions

- Should the app surface the snapshot's own age — "library last updated
  yesterday"? It is the useful half of what the withdrawn indicator did, without
  any of the ambiguity, because the age is a fact the container can state.
