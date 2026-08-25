## Why

Glimpse presents itself as an offline-capable PWA and has never worked offline.

There is a manifest, an install button, an offline fallback page, and Alpine is
vendored rather than loaded from a CDN — with a comment saying it is vendored
"precisely so the app keeps working offline". None of it buys anything. Take the
network away and the app shows **"Glimpse is not configured."**

The cause is that `config.json` and the library snapshots are fetched with a
cache fallback that can never hit: nothing ever writes them to a cache. The
fallback line exists, looks correct, and is dead. So the app loads its shell,
loads Alpine from cache exactly as designed, then cannot read its own
configuration and correctly refuses to guess — and the user, who installed this
to a home screen, gets an error page for a library that has not changed since the
last cron run.

This is the gap between what the project claims and what it does, and it is the
last unexamined corner of the rewrite.

## What Changes

- **The last configuration a container served is remembered**, and used only when
  that container cannot be reached at all. The app can then start offline and
  knows which server it is browsing.

- **A server that answers is always believed.** A cached configuration SHALL NOT
  stand in for one the server actually returned — including an error. Today's
  fallback triggers on any non-OK response, which would let a stale copy paper
  over an entrypoint that failed. That is the failure this project spent years
  on, and the distinction between *unreachable* and *reachable and broken* is the
  core of this change.

- **The library snapshots are cached the same way.** `movies.json` and
  `tvshows.json` are the app's content; without them an offline start has a
  configuration and an empty grid.

- **The user is told when they are looking at a snapshot.** A library that is
  quietly out of date is the same failure as a library that is quietly wrong —
  the user cannot tell a stale grid from a current one.

- **The offline fallback page keeps its job** for the case that remains: a client
  that has never successfully loaded, and so has nothing to fall back to.

## Capabilities

### New Capabilities

None. This is `pwa` finally meeting the promise already in its spec.

### Modified Capabilities

- `pwa`: the offline contract becomes real — what is cached, when a cached copy
  may be served, and what happens when nothing is cached.
- `application-shell`: the `config.json` contract gains one narrow, explicit
  exception. A *missing or malformed* configuration is still reported and never
  defaulted around; what changes is that an *unreachable* one may be answered
  from the last copy this client received.
- `media-browsing`: the grid may be served from a cached snapshot, and says so.

## Impact

- `web/sw.js` — the strategies for `/config.json` and `/data/*.json`, and the
  distinction between a failed fetch and a failed response.
- `web/index.html` — the offline indicator, and the boot path's handling of a
  configuration that came from cache.
- `web/offline.html` — narrowed to the never-loaded case; check its copy still
  makes sense.
- `tests/` — assertions that a non-OK response is never answered from cache, and
  that the snapshots are cached at all.

**The frozen `docker-compose.yml` surface is NOT touched.** No environment
variable is added, removed or reinterpreted. An existing user's compose file runs
this unmodified.

`web/sw.js` ships inside the image and CI builds the image only after a push, so
`make docker-smoke` is required locally first.

There is a privacy consequence worth stating plainly: the library snapshot is
already served to any client that can reach the port — the app is unauthenticated
by design — but after this change a copy persists in the browser's cache after
the user leaves the network. That is what offline means, and it is the same
trade every offline-capable reader makes. It is called out here so the decision
is deliberate rather than discovered.
