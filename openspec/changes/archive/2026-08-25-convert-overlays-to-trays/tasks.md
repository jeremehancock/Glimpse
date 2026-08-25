## 1. Foundations

- [x] 1.1 Vendor Alpine.js to `web/assets/alpine.min.js` (same version Marquee ships) and load it with `defer` from `index.html`.
- [x] 1.2 Add `x-cloak` handling so no overlay flashes visible before Alpine initialises.
- [x] 1.3 Create `web/assets/tokens.css`: surface colours, borders, radii, elevation, backdrop tint/blur, `--dur-base` / `--dur-exit` / `--dur-slow`, and the easing curves. Keep the existing per-server palette blocks working.
- [x] 1.4 Declare the overlay layering scale as documented constants so a dialog raised from a tray outranks it.
- [x] 1.5 Add the app-wide `prefers-reduced-motion` rule collapsing overlay transitions to instant.

## 2. The overlay presentation

- [x] 2.1 Create `web/assets/overlays.css` with `.sheet` (backdrop, panel, grip, handle, head, title, body) ported from Marquee.
- [x] 2.2 Add `.modal` (backdrop, panel, head, close control), including hiding the grab handle on pointer devices.
- [x] 2.3 Add the `overlay-opening` / `overlay-closing` / `overlay-shut` / `overlay-shown` transition classes, with the panel-specific rules that make a tray slide and a dialog scale.
- [x] 2.4 Set `pointer-events: none` while closing, so a dismissed overlay stops swallowing clicks during its leave animation.
- [x] 2.5 Give `.sheet__body` `overscroll-behavior: contain`.
- [x] 2.6 Suppress the focus ring on `[role="dialog"][tabindex="-1"]`, scoped so it cannot reach a control.

## 3. Behavior

- [x] 3.1 Create `web/assets/overlays.js`. Port the drag-dismiss gesture: document-level, keyed on `.sheet__grip, .sheet__head, .modal__head`, dismissing via the overlay's own backdrop click.
- [x] 3.2 Clear the inline `transition` and `transform` before triggering dismissal, in that order, so the leave animation is not outranked by the drag's inline transform.
- [x] 3.3 Port the scroll lock: pin the body, hold back the scrollbar width, restore scroll position on release.
- [x] 3.4 Make the scroll lock treat an overlay carrying the closing class as shut.
- [x] 3.5 Port the focus manager: find dialogs by `[role="dialog"]`, move focus in on open, restore on close via an ancestor chain that stops short of `<body>`.
- [x] 3.6 Focus without scrolling, and give a non-focusable ancestor a temporary negative `tabindex`, removing it again if it did not help.
- [x] 3.7 Wire Escape to close the topmost overlay only.

## 4. Convert the overlays — simplest first

- [x] 4.1 **Mobile menu** → Actions tray. Teleport it to `<body>`; the header will become a translucent surface, and `backdrop-filter` would otherwise make it a containing block for the fixed tray inside it.
- [x] 4.2 Make the menu's entries move focus to the opening control before the tray hides, for any entry that opens another overlay.
- [x] 4.3 **Server switcher** → tray, replacing the popover added by `replace-boot-time-html-rewriting`. Keep the rules: nothing for one server, a toggle for two, this tray for three.
- [x] 4.4 **Genre filter** → one tray. Delete `.genre-menu`, `.genre-dropdown`, `.genre-drawer`, `.genre-drawer-overlay` and their JS; both viewports now render from the same markup.
- [x] 4.5 Verify genre counts, the active indicator, and composition with search and sort still hold.
- [x] 4.6 **Roulette** → dialog. Keep the "nothing to select" state and its dismissal control.
- [x] 4.7 **Trailer** → dialog. Keep the loading indication; ensure dismissal stops playback.
- [x] 4.8 Make the trailer's opening control move focus first, so dismissing it returns to the detail overlay.
- [x] 4.9 **Media detail** → tray on touch, dialog on pointer. Preserve every field, the backdrop image, the genre chips and their filtering, and the trailer control's conditional presence.
- [x] 4.10 Remove the old `.modal-overlay`, `.trailer-modal-overlay`, `.roulette-overlay` and `.mobile-menu` CSS and JS now that nothing references them.

## 5. Service worker and assets

- [x] 5.1 Cache `alpine.min.js`, `tokens.css` and `overlays.css` in the service worker.
- [x] 5.2 Bump the cache version so the first load after upgrading discards the previous scheme.
- [x] 5.3 Confirm the app still loads and functions offline after the shell is cached.

## 6. Tests

- [x] 6.1 Assert every `.sheet__panel` and `.modal__panel` in the markup carries `role="dialog"`, `aria-modal="true"` and `tabindex="-1"` — the trap that makes an unmanaged overlay look identical to a managed one.
- [x] 6.2 Assert every overlay's grip/head is a sibling of its body, never an ancestor, so the drag region is not the scroller.
- [x] 6.3 Assert no overlay declares both `aria-disabled` and a tooltip on the same control.
- [x] 6.4 Assert the six overlays exist and use the shared classes rather than bespoke ones — i.e. that `.genre-drawer`, `.mobile-menu`, `.modal-overlay`, `.trailer-modal-overlay` and `.roulette-overlay` are gone.
- [x] 6.5 Assert the reduced-motion rule exists and is app-wide rather than per overlay.
- [x] 6.6 Assert `alpine.min.js` is vendored locally and referenced by a relative path — no CDN, or the PWA stops working offline.

## 7. Gates, docs, validation

- [x] 7.1 Run `make check` — ESLint now has real JavaScript to lint for the first time; fix what it finds rather than widening the ignore list.
- [x] 7.2 Run `make docker-smoke`.
- [x] 7.3 Record the overlay conventions in `CLAUDE.md`: the role/tabindex rule, the focus-before-hide rule, the separate drag region, and the closing-is-not-open rule.
- [x] 7.4 Update `README.md` if any described interaction changed.
- [x] 7.5 Verified in headless Chromium against the running container: no console errors, Alpine initialises, all six overlays render shut with role/aria-modal/tabindex, the Actions tray teleports to `<body>`, genres derive with counts, and the switcher tray lists exactly the non-active servers. Pointer/touch feel belongs to 7.7.
- [ ] 7.6 Verify with reduced motion enabled.
- [ ] 7.7 Push to `dev` and validate the `:dev` image.
