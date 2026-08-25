## 1. Survey the layering ladder

- [x] 1.1 Grep every `z-index` declaration under `web/` and write the full list
      into the change notes — value, selector, file, line. This is a survey, not
      a spot check: lowering `.header` exposes any ordering that was chosen to
      beat `100`.
- [x] 1.2 Classify each one as page chrome, overlay, or scoped-within-a-parent
      (a value that only orders siblings inside a positioned ancestor and never
      competes with an overlay).
- [x] 1.3 Confirm `--z-chrome`, `--z-sheet` and `--z-modal` in
      `web/assets/tokens.css` still describe the intended ladder, and correct the
      token comment if the survey contradicts it.

## 2. Move page chrome below the overlay scale

- [x] 2.1 Point `.header`'s `z-index` at `--z-chrome`.
- [x] 2.2 Point `.scroll-to-top`'s `z-index` (currently `1000`) at the chrome
      tier. Note it is a second, unreported instance of the same defect — it is
      not covered by overlay backdrops today either.
- [x] 2.3 Point `.swipe-indicator`'s `z-index` (currently `90`) at the chrome
      tier.
- [x] 2.4 Resolve anything else class 1.2 flagged as chrome.
- [x] 2.5 Verify at a pointer width that the detail dialog's panel and backdrop
      paint above the header.
- [x] 2.6 Verify at a touch width that the header is dimmed and blurred by an
      open tray's backdrop.

## 3. Bind the teleported tray's controls

- [x] 3.1 Move the `.sort-button` binding pass so it runs on Alpine's
      `alpine:initialized` event, after `x-teleport` has moved the Actions tray
      into `<body>`.
- [x] 3.2 Move the `renderServerSwitcher()` call that performs the initial
      binding to the same point. Keep the call made on a server change where it
      is — that one already runs late enough.
- [x] 3.3 Make the sort pass idempotent, so re-running it cannot double-bind.
      Per the design's open question, prefer assigning `onclick` over adding a
      listener, matching what `renderServerSwitcher()` already does.
- [x] 3.4 Confirm the install-button binding reaches the tray's copy. It is bound
      from a `beforeinstallprompt` handler, so it may already run late enough —
      determine which, and fix only if it does not.
- [x] 3.5 Verify at a touch width that tapping the tray's Date Added control
      re-sorts the grid, marks itself active, dismisses the tray, and returns the
      grid to the top.
- [x] 3.6 Verify with two servers configured that the tray's server control is
      labelled with the other server's name and navigates to it.
- [x] 3.7 Verify with three servers configured that the tray's server control
      opens the switcher overlay listing both others.
- [x] 3.8 Verify with one server configured that the tray holds no server
      control at all.

## 4. Serve rebuilt assets to installed clients

- [x] 4.1 Route same-origin `/assets/` requests through
      `networkFirstWithCacheFallback()` in `web/sw.js`, rather than letting them
      fall through to `cacheFirstStrategy()`.
- [x] 4.2 Keep every current entry in `STATIC_ASSETS` precached on install, so
      the offline fallback still has them — `alpine.min.js` especially.
- [x] 4.3 Bump `CACHE_NAME` and `DYNAMIC_CACHE` once, and record in the comment
      above them what is being evicted and why, in the style of the existing v7.3
      note.
- [x] 4.4 Confirm the activate handler still deletes caches whose names do not
      match the new ones.
- [x] 4.5 Verify against a rebuilt container from a profile that has already
      loaded the app: change a value in `overlays.css`, rebuild, reload, and
      confirm the new value is in force.
- [x] 4.6 Verify the app still loads with the network offline, with the overlay
      stylesheet, the overlay script and Alpine all served from cache.
- [x] 4.7 Serve `/sw.js` with `no-cache` in `config/nginx.conf`. It was matched
      by the `.js` extension rule and given a 7-day cache — a stale service
      worker freezes the caching policy of the whole app, and withholds the
      upgrade that would fix it.
- [x] 4.8 Serve `/assets/` with `no-cache` in `config/nginx.conf`. The service
      worker's network-first strategy calls plain `fetch()`, which consults the
      HTTP cache, so a 7-day `max-age` on unversioned filenames defeats it —
      neither layer looks wrong on its own.
- [x] 4.9 Fetch with `cache: 'reload'` in `networkFirstWithCacheFallback()`, and
      precache each `STATIC_ASSETS` entry the same way. Correcting the nginx
      header stops new responses being held but cannot retract an entry the
      browser was already told to keep for a week — bypassing the HTTP cache is
      what heals an already-poisoned client on its next load rather than in
      seven days.
- [x] 4.10 Confirm the response headers: `/sw.js` and `/assets/*` revalidate,
      `/images/*` and `/data/*.jpg` keep their 7-day cache, `/config.json` stays
      `no-store`.

## 5. Make the grab handle legible over artwork

- [x] 5.1 Lift `.sheet__grip` inside `.modal__fixed` out of the artwork's paint
      order, the way `.modal-header` already does.
- [x] 5.2 Extend the `.modal-backdrop-art` mask so it is fully transparent across
      the handle and for a margin below its lower edge, instead of reaching
      opacity at the handle's lower edge.
- [x] 5.3 Express that margin relative to `--grip-height` rather than as a second
      literal. Two hardcoded `17`s drift, and the symptom is an illegible handle
      on bright artwork only.
- [x] 5.4 Confirm the artwork still reaches the panel's top edge, with no band of
      bare surface above it.
- [x] 5.5 Verify at a touch width against an item with bright backdrop artwork
      that the handle reads clearly.

## 6. Tests

- [x] 6.1 Add a test asserting no page-chrome selector declares a stacking order
      at or above the lowest overlay tier. Transcribe the ladder into the test's
      own assertions rather than deriving it from the file under test — a test
      that recomputes the ladder from its subject cannot fail.
- [x] 6.2 Add a test asserting the Actions tray's controls are bound after
      teleport: that the binding passes are attached to `alpine:initialized` and
      not run at parse time.
- [x] 6.3 Add a test asserting `sw.js` does not route `/assets/` through the
      cache-first strategy, and that every `STATIC_ASSETS` entry is still
      precached.
- [x] 6.4 Add a test asserting the artwork mask clears past the handle — that its
      stop is derived from `--grip-height` and is greater than it.
- [x] 6.5 Confirm `tests/test_compose_surface.py` passes untouched. Nothing here
      adds, removes or reinterprets an environment variable.

## 7. Documentation

- [x] 7.1 Record the layering ladder in `CLAUDE.md` alongside the existing
      overlay rules — that page chrome ranks below every overlay, and that the
      numbers live in `tokens.css`.
- [x] 7.2 Record that a control inside the teleported Actions tray must be bound
      after `alpine:initialized`, and why a parse-time pass finds nothing. This
      is the failure that presents as a feature being missing.
- [x] 7.3 Record in `docs/` that `/assets/` is network-first, so a future change
      that "optimises" it back to cache-first knows what it is undoing.
- [x] 7.4 Check whether `README.md` needs anything. If nothing user-facing
      changed, say so explicitly rather than inventing an edit.

## 8. Gates

- [x] 8.1 `make fmt`, then `make lint` and `make test` — both green.
- [x] 8.2 `make docker-smoke`. `sw.js` ships in the image and CI builds the image
      only after the push.
- [ ] 8.3 Push to `dev` and validate the `:dev` image. Validate from a fresh
      browser profile — an existing one will show one stale load before the new
      service worker takes effect.
- [x] 8.4 When asking for that validation, say that the genre and server items
      still look wrong by design: their styling is the sibling change, not this
      one.
