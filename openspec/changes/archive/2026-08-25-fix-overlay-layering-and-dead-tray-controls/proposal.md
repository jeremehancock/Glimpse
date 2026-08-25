## Why

Validating the `:dev` image surfaced four defects that make the app look finished
while behaving as if it is not. An overlay opens beneath the header instead of
over it. Half the controls in the phone's Actions tray do nothing at all when
tapped — no error, no feedback, they simply close the tray. The grab handle that
dismisses the detail tray is drawn underneath the item's artwork. And a service
worker holds every browser that ever loaded the app on the CSS and JavaScript it
first saw, so a user who upgrades gets new markup driven by old behavior.

That last one is the reason this is urgent rather than merely untidy: it made a
correctly-implemented feature look broken during validation, and it will do so
again for every future release. Three changes are currently blocked on "validate
the `:dev` image", and validation cannot be trusted until it is fixed.

## What Changes

- **Page chrome moves below the overlay layer.** The header, the scroll-to-top
  button and the swipe indicator currently outrank every overlay, so the detail
  dialog renders under the header on a desktop and every tray on a phone slides
  in behind a header that stays lit and unblurred above the backdrop. All three
  move onto the chrome tier the design tokens already declare.

- **Controls inside the Actions tray are bound after the tray exists.** The tray
  is teleported into `<body>` when Alpine boots, which happens after the page's
  own wiring pass has already run and found nothing. The sort controls, the
  server switcher and the install button in that tray have never had handlers.
  Binding moves to a point where the teleported markup is present.

- **Static assets are fetched network-first with a cache fallback**, the strategy
  the app shell already uses, instead of cache-first. Offline capability is
  unaffected; a rebuilt asset is picked up on the next load rather than never.
  The cache name is bumped once to discard entries already poisoned.

- **The detail tray's grab handle is drawn above the item's artwork.** It is
  lifted out of the artwork's paint order, and the artwork's fade is extended
  past the handle rather than ending at its lower edge.

No behavior is removed and nothing is renamed. There is no **BREAKING** change.

## Capabilities

### New Capabilities

None. Every defect here is an existing capability not meeting its own spec.

### Modified Capabilities

- `visual-design`: adds the requirement that page chrome ranks below every
  overlay on the layering scale, and that a control presented inside a teleported
  overlay is operable there.
- `sorting`: the sort controls offered inside the Actions tray apply the sort,
  rather than only dismissing the tray.
- `multi-server`: the server switcher inside the Actions tray is labelled from
  configuration and performs the switch, at every width it is offered.
- `pwa`: the service worker serves a rebuilt static asset rather than an
  indefinitely cached copy, while keeping the app usable offline.
- `media-detail`: the grab handle stays legible against any item's artwork.
- `genre-filter`: choosing a genre returns the grid to its beginning. Found while
  implementing the sort fix — the two controls shared the defect, because an
  action taken inside an overlay cannot scroll a page the overlay has pinned.

## Impact

- `web/index.html` — the z-index values on `.header`, `.scroll-to-top` and
  `.swipe-indicator`; the `.modal-backdrop-art` mask and the grip's paint order;
  the point at which `.sort-button`, `.server-toggle-button` and the install
  button are bound.
- `web/assets/tokens.css` — the `--z-chrome` token, currently declared and
  unused, becomes load-bearing.
- `web/sw.js` — the static-asset fetch strategy and `CACHE_NAME`.
- `tests/` — new assertions for the layering order and for the teleported tray's
  controls carrying handlers.

**The frozen `docker-compose.yml` surface is NOT touched.** No environment
variable is added, removed or reinterpreted; `tests/test_compose_surface.py`
should pass unchanged. An existing user's compose file runs this unmodified.

`web/sw.js` ships inside the image, so `make docker-smoke` is required locally
before pushing — CI builds the image only after the push.

Users upgrading will silently re-download the app's CSS and JavaScript once, on
their first load after the upgrade, because the cache name changes. There is
nothing for them to do.
