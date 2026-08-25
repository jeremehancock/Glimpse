## Context

The app has every marker of an offline-capable PWA and no offline capability.

Measured against a container built from `dev`, with the network disabled via CDP:
the shell loads from cache, Alpine loads from cache, `tokens.css` and
`overlays.css` load from cache — and the page reads:

> **Glimpse is not configured.** The application could not read /config.json,
> which the container generates at startup.

That is the app behaving correctly. `reportConfigError()` fires because the
configuration genuinely was not readable, and refusing to guess is the right
call. The defect is upstream: nothing ever made the configuration available.

```
/config.json      alwaysFreshStrategy  →  fetch(no-store), then caches.match()
/data/*.json      alwaysFreshStrategy  →  same
                                              ↑
                        nothing ever writes either one to a cache,
                        so this fallback has never returned anything
```

Both fallbacks are live code that cannot succeed. They look like offline support
and are the reason nobody noticed there wasn't any.

A second problem sits in the same function, and it is the more dangerous one.
`alwaysFreshStrategy` falls back to cache on **any non-OK response**, not only on
a failed fetch:

```js
if (response.ok) { return response; }
const cachedResponse = await caches.match(request);
return cachedResponse || response;          // ← a 500 becomes a stale 200
```

Today that line is inert because the cache is always empty. Populate the cache —
which is exactly what this change does — and it becomes a mechanism for hiding a
broken entrypoint behind the last configuration that worked. Fixing the offline
gap without fixing this would install the project's oldest failure mode in new
clothes.

## Goals / Non-Goals

**Goals:**

- An installed client that has loaded successfully once can open with no network
  and browse the library.
- A server that answers is always believed, whatever it says.
- The user can tell a cached session from a live one.
- Tests that fail if an error response is ever answered from cache.

**Non-Goals:**

- Making the app work offline on first run. There is nothing to show; the offline
  page is the correct answer and keeps that job.
- Caching artwork more aggressively. It is already stale-while-revalidate, which
  is right for content addressed by a stable path.
- Background sync, update notifications, or any "new data available" prompt. The
  snapshot changes on a cron; a user who reloads gets it.
- Any change to what the fetchers write or how often.
- Authentication. The app is unauthenticated by design and this does not revisit
  that.

## Decisions

### 1. Split "could not reach" from "answered badly"

One `try`/`catch` boundary already separates them and the current code crosses
it. A thrown fetch is unreachable; a returned response — 200, 404, 500 — is an
answer.

```
fetch() throws              →  unreachable  →  cache is allowed to answer
fetch() returns, !ok        →  answered     →  return it, cache stays out
fetch() returns, ok         →  answered     →  return it, update the cache
```

**Alternative considered:** treat 5xx as unreachable and 4xx as answered.
Rejected — a 500 from the container is precisely the "entrypoint failed" case the
user must see. The status is the server speaking; the absence of a status is the
network.

This is stated as a requirement rather than left to the implementation because it
is invisible in testing: both paths look identical to a user on a working
network, and the wrong one only shows up on the day something is broken.

### 2. `config.json` is cached, and it is not a default

`CLAUDE.md` is unambiguous: *"A missing or malformed `config.json` is reported,
never defaulted around."* This change does not weaken that, and the distinction
is worth being precise about because it is the reason this is a spec change
rather than a wiring decision.

| | Source | Allowed |
| --- | --- | --- |
| Default | Invented by the app | **No** — unchanged |
| Inferred | Guessed from environment or URL | **No** — unchanged |
| Missing / malformed | Server answered, badly | **Reported** — unchanged |
| Last received | This container told this client, earlier | **Yes** — new |

A cached configuration is a fact about this container, recorded from its own
answer. It cannot describe a server that was never configured, cannot invent a
primary, and cannot appear on a client that has never successfully loaded. The
failure the rule guards against — an install that looks like it works while
showing the wrong library — requires the app to make something up, and nothing
here does.

The one genuine risk: an admin changes the environment, restarts, and a client
holds the previous configuration. But that client only uses the cached copy when
it cannot reach the container at all — and a container it cannot reach is not one
that just restarted with new settings and is waiting to be seen. When it comes
back, it answers, and the answer wins.

### 3. The snapshots are cached too, or the configuration buys nothing

Caching `config.json` alone produces an app that starts offline, knows which
server it is browsing, and shows an empty grid. Worse than the error it replaces,
because an empty grid is indistinguishable from a library with no items — the
exact ambiguity the project already treats as a defect.

So `movies.json` and `tvshows.json` get the same treatment. They are the natural
candidate: a snapshot written on a cron schedule is already stale by design, so
serving the last one is a difference of degree, not of kind.

Artwork is already cached stale-while-revalidate, so a cached snapshot renders
with its posters. That is why this works at all and is worth not breaking.

### 4. The indicator is required, not polish

An app that silently shows old data is the failure this project keeps
rediscovering in different forms. A user who opens Glimpse on a train and does
not see the film they added last night must be able to tell "you are offline"
from "the fetcher is broken".

It clears when the app next reaches the server, so it reports current state
rather than a flag set once at boot.

**Alternative considered:** a timestamp — "as of 3 hours ago". Rejected for now;
the snapshot's own age is not the same as the cache's age, and showing one as the
other would be a new kind of wrong. Whether the app should surface snapshot age
at all is a separate question worth asking later.

## Risks / Trade-offs

- **A poisoned cache could outlive a fix.** If a bad-but-successful config is
  ever cached, the client keeps it until it reaches the server again. → It only
  serves while unreachable, and any successful response replaces it. The window
  closes the moment the container is reachable.

- **The library persists in the browser after the user leaves the network.**
  Titles, artwork and summaries sit in the cache. → Stated in the proposal so the
  decision is deliberate. It is the same trade every offline reader makes, and
  the data is already served unauthenticated to anyone who can reach the port.
  Worth a line in the README rather than a silent change.

- **Cache size on a large library.** `movies.json` for a few thousand items is
  well within quota; artwork already dominates and is unchanged. → Measure
  against the seeded 400-item fixture and reason up; add nothing until there is a
  number.

- **The offline page becomes hard to reach in testing.** It now only appears for
  a client that never loaded successfully. → Test it explicitly with a fresh
  profile, or it will rot the way the inlined copy in `sw.js` did.

- **This lands on top of an unvalidated `:dev`.** Three changes are already
  waiting on validation. → Sequence it last, and validate it separately: offline
  behavior is the one thing that cannot be checked by looking at the app on a
  working network.

## Migration Plan

No data migration, no configuration change, no compose change. An ordinary image
rebuild.

On first load after upgrade the worker begins caching the configuration and
snapshots as it fetches them, so offline capability arrives on the *second* load,
not the first. That is inherent — there is nothing to serve until something has
been received — and is worth stating so it is not read as the change not working.

Rollback is reverting the commit and rebuilding. Clients keep a cache the new
worker will no longer read; the activate handler's existing name check clears it
on the next cache-name change.

## Open Questions

- Should the app surface the snapshot's own age — "library last updated
  yesterday" — independently of whether this session is offline? It is arguably
  more useful than the offline indicator and is a different question.
- Should `checksums.pkl`-style staleness ever be exposed to the user, or does
  that leak an implementation detail they cannot act on?
- Does the offline indicator belong in the header, where it is always visible, or
  as a dismissible notice? Leaning header: a dismissible notice about stale data
  is a notice that gets dismissed and then forgotten.
