## Why

Swiping between Movies and TV Shows is an instant cut: the grid the viewer was
reading vanishes and a different one is simply there, already scrolled to the
top. Nothing on screen connects the gesture to its result, so a swipe that
worked and a swipe that mis-fired look identical — the app relies on a toast
appearing a moment later to tell the viewer which tab they are on. Making the
outgoing grid leave in the direction of the swipe answers that on screen, with
the motion the gesture already implies.

## What Changes

- The touch swipe between tabs animates: the outgoing grid slides out in the
  direction of the swipe as the incoming grid slides in behind it. The gesture
  itself is unchanged — same threshold, same angle test, same commit point.
- `switchTab()` renders the incoming tab **before** handing it the active
  class, rather than after. Today the outgoing tab is hidden first and the
  incoming one is rendered into an already-visible container; a transition
  needs both laid out at once, with the incoming already holding its content.
- `filterAndSortMedia()` takes the tab to render as an argument instead of
  reading `.tab.active`, so a tab can be rendered while it is not the active
  one. All existing call sites keep today's behavior by passing the active tab.
- The scroll-to-top that accompanies a tab switch happens **during** the
  transition rather than after it, at the one moment nothing on screen reflects
  the page's scroll position. It stays routed through
  `window.GlimpseOverlays.scrollPageTo()`.
- Desktop tab clicks keep the instant cut. The animation is gated on the same
  condition that binds the swipe gesture, so the two cannot drift apart.
- `.content`'s existing `opacity` / `translateY` transition is resolved. It has
  never run — a `display: none` to `display: block` swap does not transition —
  so it is a rule that appears to animate the tabs and does not.

Not in scope: a finger-following drag where the grids track the touch and
settle. The gesture stays discrete and fires once on commit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-browsing`: adds a requirement covering what a tab switch looks like —
  that a committed swipe animates in the direction of the gesture, that the
  incoming tab is fully rendered before any of it is visible, that the pointer
  path is unaffected, and that the animation and the gesture are gated
  together. The spec today describes the grid, its windowing bound and its
  entrance animation, but says nothing about switching tabs at all.

## Impact

- `web/index.html`: `switchTab()`, `filterAndSortMedia()` and its five call
  sites, the swipe handler's commit branch, the `.content` CSS rule, and new
  CSS for the transition. Nothing outside the tab-switching path.
- `tests/`: a new test pinning the source decisions this change makes, in the
  style of `tests/test_grid_windowing.py` — `make test` has no browser and
  cannot observe a transition, so the browser half of the verification is
  `tools/browser.py` driving a real Chromium over CDP against a seeded library.
- **Does not touch the frozen `docker-compose.yml` surface.** No new
  environment variable, no change to an existing one, no new file to mount. An
  existing user's compose file is unaffected.
- No new dependency and no build step: the transition is CSS the browser reads
  as authored, and it inherits the app-wide reduced-motion rule already in
  `web/assets/tokens.css`.
- Carries a measurement gate. The approach transforms an element whose layout
  box is as tall as the whole library — over a million pixels at library scale.
  If that cannot be composited smoothly, the fallback is a cross-fade rather
  than a slide, and that is decided by measurement before the CSS is written.
