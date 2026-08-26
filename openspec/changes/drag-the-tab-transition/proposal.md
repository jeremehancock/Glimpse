## Why

Swiping between Movies and TV Shows is still a discrete gesture wearing an
animation. Nothing moves while the thumb is down; the finger lifts, the app
decides, and only then does a 280ms slide play back what was decided. So the
viewer cannot see whether the swipe is working, cannot see how far they have to
go, and cannot change their mind — the two states are "nothing is happening" and
"it already happened".

Every app the viewer holds this phone to do anything else with moves the page
with their thumb. The grid should too.

## What Changes

- **The tabs follow the finger.** Once a touch is recognised as horizontal, the
  outgoing tab tracks it one-to-one and the incoming tab enters behind it with a
  parallax lag, both updating every frame until the thumb lifts.
- **The thumb-down lift.** As the gesture is claimed, the moving tab drops back
  — a small scale, elevation and corner radius, with the page beneath dimming —
  so it reads as a card being pushed aside rather than a page repainting.
- **The gesture commits on intent, not on a fixed distance.** A lift past a
  third of the viewport commits; so does a fast flick that has travelled much
  less. Anything else settles back with the tab returning to where it was and
  the tab unchanged.
- **The gesture can be abandoned.** Dragging out and back, or lifting short,
  returns the outgoing tab to rest. This is the part that does not exist today
  at all: the current threshold is evaluated once, after the fact.
- **The axis is decided once, early, and held.** Today `touchmove` claims the
  gesture only after 100px of horizontal travel, which is too late to drive a
  drag and lets the page begin scrolling first. The axis is resolved within the
  first few pixels and locked for the rest of the touch, so a vertical scroll is
  never stolen and a horizontal drag is never handed back.
- **Rubber-banding at the ends.** Swiping right on Movies or left on TV Shows
  has nowhere to go. It resists rather than doing nothing, which is how the
  viewer learns there is nothing there.
- **The grid's window is frozen for the gesture's duration.** The lift's scale
  moves every card's measured position, which is the sole input to the
  windowing arithmetic. Rather than forbidding the scale, the change states the
  precondition and enforces it: nothing re-windows while a tab drag is live.
- **The committed settle keeps today's transition.** The freeze, the two-frame
  separation, the instant scroll reset and the idempotent teardown are all
  retained — the drag replaces what *starts* the slide, not the slide.
- **The first-load swipe tip stays.** It was dropped during implementation on
  the reasoning that a drag demonstrates itself, and restored: it only
  demonstrates itself to a viewer who already tries it, and the gesture has no
  visible affordance at rest.

Not in scope: per-tab scroll memory, a third tab, pointer drag on desktop, and
any change to how items are filtered, sorted or windowed beyond the freeze.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-browsing`: the requirement "A committed swipe moves the grid in the
  direction of the gesture" describes a transition that plays *after* a gesture
  resolves. It is replaced by requirements covering a gesture that is itself the
  transition: the tabs track the touch, the gesture can be abandoned, the axis
  is committed once and held, the ends resist, and the window does not move
  while the tabs do. The requirements covering render-before-visible, the
  hidden scroll reset, the shared gate with the gesture, and correctness
  independent of the animation are all retained — a drag makes them harder to
  satisfy, not less necessary.
- `visual-design`: adds the drag's presentation to the motion contract — the
  lift and its scrim, that the settle is timed from the distance still to
  travel rather than a fixed duration, and what reduced motion does to a
  gesture the viewer is driving with their own thumb (the follow is direct
  manipulation and stays; the settle collapses).

## Impact

- `web/index.html`: the swipe block (`touchstart` / `touchmove` / `touchend`),
  `switchTabAnimated()` split into a setup / track / settle trio,
  `updateGridWindow()`'s new guard, and the `.tab-leaving` / `.tab-entering` /
  `.tab-sliding` CSS. Nothing outside the tab-switching path.
- `web/assets/tokens.css`: tokens for the lift's scale, the scrim, and the
  settle's velocity floor. Existing `--dur-tab` is retained and reused.
- `tests/test_tab_transition.py`: extended rather than replaced. The decisions
  it pins — no geometry read after the freeze, horizontal translate on the
  slide, layer promotion on the setup state, idempotent teardown — all still
  hold, and the drag adds several of its own.
- `tools/browser.py`: needs touch dispatch over CDP to drive the gesture. `make
  test` has no browser and cannot observe a drag; the behavioural half of the
  verification is a real Chromium against a seeded library, as it was for the
  transition this builds on.
- **Does not touch the frozen `docker-compose.yml` surface.** No new
  environment variable, no change to an existing one, no new file to mount. An
  existing user's compose file is unaffected.
- No new dependency and no build step. The drag is authored JS and CSS that
  nginx serves as written.
- Carries a measurement gate on one number. The incoming tab's render is
  ~90ms at 7,000 items, and the drag moves it from touch-*end* to the moment
  the gesture is claimed — from a moment nothing is moving to the first frame
  of a gesture the thumb is driving. If it is felt there, memoising the
  filtered-and-sorted list is the named lever, and it is decided by measurement
  before the drag ships.
