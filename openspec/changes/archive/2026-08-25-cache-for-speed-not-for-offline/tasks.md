## 1. Separate "unreachable" from "answered badly"

- [x] 1.1 Rewrite `alwaysFreshStrategy()` in `web/sw.js` so a non-OK response is
      returned as-is and never replaced by a cached copy.
- [x] 1.2 Apply the same rule to `networkFirstWithCacheFallback`. It had the
      identical defect and it is wrong there for the identical reason: a shell
      served from cache over a 500 hides a container whose entrypoint failed.
      One rule, every strategy.
- [x] 1.3 Write the distinction into the comments in the terms the design uses:
      a status is the server speaking, the absence of a status is the network.
- [x] 1.4 Rename the function. `alwaysFreshStrategy` was not the problem, but the
      name had to match what survived. → `networkOnlyStrategy`.

## 2. Stop pretending to cache the library data

- [x] 2.1 Delete the cache fallback from the `/config.json` route. It had never
      returned anything and could not: nothing wrote to that cache.
- [x] 2.2 Delete it from the `/data/*.json` route too.
- [x] 2.3 Do NOT replace either with a working fallback. Withdrawn — see design
      decision 0. The app shows the container's answer or an error.
- [x] 2.4 Make sure neither route writes to a cache either. An entry nothing can
      read back is the same defect inverted.
- [x] 2.5 Keep both routes checked BEFORE the cache-first fallback at the bottom
      of the fetch handler, or `config.json` gets served cache-first and a
      restart with new settings is never seen.
- [x] 2.6 Record in `web/index.html` that a synchronous XHR is invisible to a
      service worker, so the next person does not spend a session rediscovering
      it. Measured: an async `fetch()` of the same URL is intercepted and cached;
      the synchronous read is not.

## 3. Keep — and pin — what makes the app fast

- [x] 3.1 Confirm artwork is still stale-while-revalidate. This is the whole
      performance story: a repeat visit paints its grid with zero poster
      requests.
- [x] 3.2 Confirm the app's own CSS and JS stay network-first with a cache
      fallback, sharing the app shell's strategy so the two cannot drift.
- [x] 3.3 Confirm the precache still carries Alpine, the overlay assets, the
      manifest and the offline page.
- [x] 3.4 Bump `CACHE_NAME` and `DYNAMIC_CACHE` to `v8.3`, so a client that ran
      the withdrawn build does not keep library JSON nothing will read.

## 4. Tests

- [x] 4.1 Assert no strategy answers a non-OK response from cache. Pinned by
      shape — no cache read inside any strategy's `try` — so it survives a
      rename. It already did survive one.
- [x] 4.2 Assert the data routes neither read from nor write to a cache.
- [x] 4.3 Assert only successful responses are ever cached.
- [x] 4.4 Assert artwork is stale-while-revalidate and assets share the shell's
      strategy.
- [x] 4.5 Assert the data routes are checked before the cache-first fallback.
- [x] 4.6 Assert the offline page is precached and served only from a `catch`.
- [x] 4.7 Mutate every assertion to confirm it fails when the defect is
      reintroduced. → 11 mutations, all caught.
- [x] 4.8 Confirm `tests/test_compose_surface.py` passes untouched.
- [x] 4.9 Rename the test file to match what it now asserts →
      `tests/test_cache_policy.py`.

## 5. Documentation

- [x] 5.1 Record in `CLAUDE.md` that the worker is for speed, what is cached,
      what is never cached, and why adding a data cache fallback is a product
      decision rather than a wiring one.
- [x] 5.2 Record that a non-OK response is never served from cache, and why that
      is load-bearing rather than tidy.
- [x] 5.3 Record that a synchronous XHR is invisible to a service worker.
- [x] 5.4 Remove the offline claims from `README.md` — they described the
      withdrawn behavior.
- [x] 5.5 Update `docs/docker.md`: `config.json` is network-only in the worker,
      so `no-store` in nginx is the whole policy rather than half of one.
- [x] 5.6 Update `docs/handover.md` — punch-list item 4 and the change inventory.

## 6. Gates

- [x] 6.1 `make fmt`, then `make lint` and `make test` — both green. `make lint`
      needs Node 18+.
- [x] 6.2 `make docker-smoke`.
- [ ] 6.3 Push to `dev` and validate the `:dev` image.

## 7. Verification performed

Driven against a real browser over CDP with a container seeded to 400 movies and
250 shows. **11/11 checks.**

Measured by reading the container's **nginx access log**, not the timing API.
`PerformanceResourceTiming.transferSize` reads 0 for anything a service worker
handled, cached or not, and measuring that way reported the snapshots as cache
hits when they were not — a green result for the opposite of the truth.

| | Requests reaching the container on a repeat visit |
| --- | --- |
| Posters | **0** (15 rendered from cache) |
| Snapshots | 2 |
| `config.json` | 1 |
| CSS / JS | 4 (revalidated, 106 ms total) |

Also confirmed: `config.json` and the snapshots appear in no Cache API cache, and
a **stopped container produces the configuration error page with zero cards** —
never a stale library.
