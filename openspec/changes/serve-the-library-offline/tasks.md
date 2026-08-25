## 1. Separate "unreachable" from "answered badly"

- [ ] 1.1 Rewrite `alwaysFreshStrategy()` in `web/sw.js` so a non-OK response is
      returned as-is and never replaced by a cached copy. Today it falls back on
      any non-OK status, which is inert only because the cache is empty — the
      moment this change populates the cache, that line becomes a mechanism for
      hiding a failed entrypoint behind the last configuration that worked.
- [ ] 1.2 Keep the cache fallback on a THROWN fetch. That is the unreachable
      case, and it is the one this change is for.
- [ ] 1.3 Write the distinction into the comment above the function, in the terms
      the design uses: a status is the server speaking, the absence of a status
      is the network. It is invisible on a working network and only shows up on
      the day something is broken.
- [ ] 1.4 Rename the function. `alwaysFreshStrategy` stops being true once it can
      answer from cache, and a name that lies is how the next person reintroduces
      the bug.

## 2. Cache what the app needs to start

- [ ] 2.1 Write successful `/config.json` responses to a cache. Only successful
      ones — never an error, never a malformed body.
- [ ] 2.2 Write successful `/data/*.json` snapshot responses to a cache, the same
      way.
- [ ] 2.3 Confirm artwork is still stale-while-revalidate, so a cached snapshot
      renders with its posters rather than as a grid of gaps. This is why the
      whole thing works; do not change it.
- [ ] 2.4 Decide which cache these live in — the versioned static cache or the
      dynamic one — and make sure the activate handler's cleanup still reaches
      it. Data outliving a cache-name bump would be a second staleness bug.
- [ ] 2.5 Verify with the network disabled that a client which has loaded before
      starts, reads its configuration, and renders the grid with artwork.
- [ ] 2.6 Verify search, sorting and the genre filter all work against the cached
      snapshot.

## 3. Keep a broken install visible

- [ ] 3.1 Verify that a container answering `/config.json` with a 500 produces
      the configuration error page, on a client that HAS a cached configuration.
      This is the single most important check in the change — it is the failure
      mode the project spent years on, reached from a new direction.
- [ ] 3.2 Verify the same for a malformed body: valid HTTP, invalid JSON.
- [ ] 3.3 Verify a first boot with no network and no cache still reports, and
      shows the offline fallback page rather than a blank screen.
- [ ] 3.4 Verify that once the container is reachable again, its answer wins and
      the cached copy is replaced.

## 4. Say when the data is not live

- [ ] 4.1 Track whether this session started from cached configuration or a
      cached snapshot.
- [ ] 4.2 Show an indication while that is true. Per the design's open question,
      prefer the header over a dismissible notice — a dismissible notice about
      stale data is one that gets dismissed and then forgotten.
- [ ] 4.3 Clear it once the app has reached the server successfully, so it
      reports current state rather than a flag set at boot.
- [ ] 4.4 Make sure it is announced to assistive technology, not conveyed by
      colour alone.
- [ ] 4.5 Verify it appears offline and clears when the network returns.

## 5. The offline page

- [ ] 5.1 Re-read `web/offline.html` now that it only appears for a client that
      has never successfully loaded. Its copy currently addresses a general
      offline case that no longer reaches it.
- [ ] 5.2 Verify it still renders, from a fresh profile with the network
      disabled. It will rot the way the inlined copy in `sw.js` did if nothing
      exercises it.

## 6. Tests

- [ ] 6.1 Add a test asserting no strategy in `sw.js` answers a non-OK response
      from cache. Pin it by shape, not by function name — this is the assertion
      that has to survive a refactor.
- [ ] 6.2 Add a test asserting `/config.json` and `/data/*.json` are written to a
      cache on success.
- [ ] 6.3 Add a test asserting only successful responses are cached.
- [ ] 6.4 Add a test asserting the offline fallback page is still reachable as a
      last resort.
- [ ] 6.5 Mutate each new assertion to confirm it fails when the defect is
      reintroduced. Two tests in an earlier change passed against reintroduced
      defects until they were mutation-checked.
- [ ] 6.6 Confirm `tests/test_compose_surface.py` passes untouched.

## 7. Documentation

- [ ] 7.1 Record in `CLAUDE.md` the exact boundary of the `config.json`
      exception: last-received is not a default, an unreachable server may be
      answered from cache, and a server that answers is always believed. The
      existing rule stays; this narrows rather than replaces it.
- [ ] 7.2 Record that a non-OK response is never served from cache, and why that
      is load-bearing rather than tidy.
- [ ] 7.3 Update `README.md`: the app now works offline after its first
      successful load, and the library is cached in the browser. State the
      persistence plainly — it is a change in what leaves the network.
- [ ] 7.4 Check whether `docs/docker.md` needs anything, given `/config.json`
      keeps its `no-store` header while gaining a service-worker cache. Those two
      are not in conflict, but the pairing deserves a sentence or someone will
      "fix" one of them.

## 8. Gates

- [ ] 8.1 `make fmt`, then `make lint` and `make test` — both green. `make lint`
      needs Node 18+.
- [ ] 8.2 `make docker-smoke`. `sw.js` ships in the image and CI builds the image
      only after the push.
- [ ] 8.3 Push to `dev` and validate the `:dev` image. Validate offline behavior
      explicitly — it is the one thing that cannot be checked by looking at the
      app on a working network, which is exactly why this defect survived to now.
