## 1. Separate "unreachable" from "answered badly"

- [x] 1.1 Rewrite `alwaysFreshStrategy()` in `web/sw.js` so a non-OK response is
      returned as-is and never replaced by a cached copy. Today it falls back on
      any non-OK status, which is inert only because the cache is empty — the
      moment this change populates the cache, that line becomes a mechanism for
      hiding a failed entrypoint behind the last configuration that worked.
- [x] 1.2 Keep the cache fallback on a THROWN fetch. That is the unreachable
      case, and it is the one this change is for.
- [x] 1.3 Write the distinction into the comment above the function, in the terms
      the design uses: a status is the server speaking, the absence of a status
      is the network. It is invisible on a working network and only shows up on
      the day something is broken.
- [x] 1.4 Rename the function. `alwaysFreshStrategy` stops being true once it can
      answer from cache, and a name that lies is how the next person reintroduces
      the bug. → `networkOnlyWithOfflineFallback`.
- [x] 1.5 Apply the same rule to `networkFirstWithCacheFallback`. It had the
      identical defect and it is wrong there for the identical reason: a shell
      served from cache over a 500 hides a container whose entrypoint failed.
      One rule, every strategy.

## 2. Retain what the app needs to start

**Revised during implementation — see design decision 2a.** The worker cannot
retain `config.json`: a browser dispatches no fetch event for a synchronous XHR,
and the boot read is one, because the theme has to be applied before first paint.
The worker holds the snapshots; the page holds the configuration.

- [x] 2.1 Retain a successful `/config.json` body in `localStorage` at boot.
      Only a parsed 2xx body — never an error, never a body that would not
      parse.
- [x] 2.2 Write successful `/data/*.json` snapshot responses to a cache in the
      service worker.
- [x] 2.3 Confirm artwork is still stale-while-revalidate, so a cached snapshot
      renders with its posters rather than as a grid of gaps. This is why the
      whole thing works; do not change it. → verified, 15/15 posters decoded
      offline.
- [x] 2.4 Decide which cache these live in — the versioned static cache or the
      dynamic one — and make sure the activate handler's cleanup still reaches
      it. Data outliving a cache-name bump would be a second staleness bug.
      → `DYNAMIC_CACHE`: received data, not precached shell, and the activate
      handler spares only the two current names, so a bump evicts it.
- [x] 2.5 Verify with the network disabled that a client which has loaded before
      starts, reads its configuration, and renders the grid with artwork.
      → container stopped, 400 cards with posters, at 1280px and 390px.
- [x] 2.6 Verify search, sorting and the genre filter all work against the cached
      snapshot. → all three, against the cached snapshot with the container down.
- [x] 2.7 Give the configuration its own worker route that neither reads nor
      writes a cache. Sharing the snapshots' strategy would write an entry
      nothing can ever read back — live code that cannot succeed, which is the
      defect this change exists to remove. The route still has to exist, or
      `config.json` falls through to the cache-first branch.

## 3. Keep a broken install visible

- [x] 3.1 Verify that a container answering `/config.json` with a 500 produces
      the configuration error page, on a client that HAS a cached configuration.
      This is the single most important check in the change — it is the failure
      mode the project spent years on, reached from a new direction. → verified
      against a real 500 with the retained copy present.
- [x] 3.2 Verify the same for a malformed body: valid HTTP, invalid JSON.
      → verified; the retained copy is deliberately not cleared, and is still
      not consulted.
- [x] 3.3 Verify a first boot with no network and no cache still reports, and
      shows the offline fallback page rather than a blank screen. → **the
      premise was wrong.** A client that has never loaded has no service worker
      registered, so nothing can serve `offline.html` and the browser's own
      error page is what appears. No code reaches that case. The page's real
      audience is a client whose worker IS installed asking for a page it never
      cached, which was verified instead (see 5.2).
- [x] 3.4 Verify that once the container is reachable again, its answer wins and
      the cached copy is replaced.

## 4. Say when the data is not live

- [x] 4.1 Track whether this session started from cached configuration or a
      cached snapshot. → the retained-config path sets it at boot; the snapshot
      responses carry `X-Glimpse-From-Cache` from the worker.
- [x] 4.2 Show an indication while that is true. Per the design's open question,
      prefer the header over a dismissible notice — a dismissible notice about
      stale data is one that gets dismissed and then forgotten. → header, and it
      shortens to "Offline" below 768px where the bar is one 70px row.
- [x] 4.3 Clear it once the app has reached the server successfully, so it
      reports current state rather than a flag set at boot. → the `online` event
      reloads the snapshots, and the badge is set from what actually arrived. A
      badge cleared without a reload would tell the truth about the connection
      and a lie about the library.
- [x] 4.4 Make sure it is announced to assistive technology, not conveyed by
      colour alone. → `role="status"`, text plus an `aria-hidden` dot, and amber
      rather than the server's brand colour so the one state worth noticing is
      not the same colour as the six that are fine.
- [x] 4.5 Verify it appears offline and clears when the network returns.
      → verified both, including clearing without a reload.

## 5. The offline page

- [x] 5.1 Re-read `web/offline.html` now that it only appears for a client that
      has never successfully loaded. Its copy currently addresses a general
      offline case that no longer reaches it. → rewritten; the old copy claimed
      the app needs a connection, which is now false for every device that can
      still reach this page.
- [x] 5.2 Verify it still renders, from a fresh profile with the network
      disabled. It will rot the way the inlined copy in `sw.js` did if nothing
      exercises it. → a fresh profile does NOT reach it (see 3.3). Verified the
      case that does: an installed worker, network gone, a route never cached.

## 6. Tests

- [x] 6.1 Add a test asserting no strategy in `sw.js` answers a non-OK response
      from cache. Pin it by shape, not by function name — this is the assertion
      that has to survive a refactor. → the invariant is that no cache is read
      inside a strategy's `try`; reads belong before the fetch or in the
      `catch`. It survived the rename in 1.4 without an edit.
- [x] 6.2 Add a test asserting `/data/*.json` is written to a cache on success,
      and that `/config.json` is NOT — an entry the worker can never serve back
      is the defect this change removes, wearing a different hat.
- [x] 6.3 Add a test asserting only successful responses are cached.
- [x] 6.4 Add a test asserting the offline fallback page is still reachable as a
      last resort.
- [x] 6.5 Mutate each new assertion to confirm it fails when the defect is
      reintroduced. Two tests in an earlier change passed against reintroduced
      defects until they were mutation-checked. → 16 mutations; **2 survived the
      first pass** and both assertions were rewritten. `"'/offline.html'" in sw`
      also matched the `caches.match('/offline.html')` the same test required,
      and the header-name assertion matched a constant declaration that survived
      gutting the read.
- [x] 6.6 Confirm `tests/test_compose_surface.py` passes untouched.
- [x] 6.7 Add tests for the retained configuration: that it exists, that it is
      gated on `else if (!answered)` and nothing else, and that it is written
      only from a parsed 2xx body.

## 7. Documentation

- [x] 7.1 Record in `CLAUDE.md` the exact boundary of the `config.json`
      exception: last-received is not a default, an unreachable server may be
      answered from cache, and a server that answers is always believed. The
      existing rule stays; this narrows rather than replaces it.
- [x] 7.2 Record that a non-OK response is never served from cache, and why that
      is load-bearing rather than tidy.
- [x] 7.3 Update `README.md`: the app now works offline after its first
      successful load, and the library is cached in the browser. State the
      persistence plainly — it is a change in what leaves the network.
- [x] 7.4 Check whether `docs/docker.md` needs anything, given `/config.json`
      keeps its `no-store` header while gaining a service-worker cache. Those two
      are not in conflict, but the pairing deserves a sentence or someone will
      "fix" one of them. → written up, adjusted for the fact that the worker
      does not cache `config.json` at all.
- [x] 7.5 Record in `CLAUDE.md` that the configuration is retained by the page
      and the snapshots by the worker, and that a synchronous XHR is invisible
      to a service worker. Someone will try to unify them otherwise, and it
      fails silently: the app looks correct on every online load.

## 8. Gates

- [x] 8.1 `make fmt`, then `make lint` and `make test` — both green. `make lint`
      needs Node 18+.
- [x] 8.2 `make docker-smoke`. `sw.js` ships in the image and CI builds the image
      only after the push.
- [ ] 8.3 Push to `dev` and validate the `:dev` image. Validate offline behavior
      explicitly — it is the one thing that cannot be checked by looking at the
      app on a working network, which is exactly why this defect survived to now.

## 9. Verification performed

Driven against a real browser over CDP with a container seeded to 400 movies and
250 shows, stopping the container rather than emulating a network condition — a
stopped container is a genuine `fetch()` throw, which is the case the whole
change turns on. **30/30 checks**, at 1280px and repeated at 390px.

The gap this caught: the first implementation cached the snapshots correctly and
the configuration not at all, so the offline start still showed "Glimpse is not
configured". Nothing in the source or the test suite said so — see decision 2a.
