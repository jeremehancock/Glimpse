## Context

`switchTab()` in `web/index.html` runs six steps in this order:

```
1. .tab.active     ──▶ moves to the incoming tab
2. .content.active ──▶ outgoing display:none, incoming display:block   (instant)
3. genre reconcile + updateGenreUI()
4. filterAndSortMedia()  ─▶ reads .tab.active, renders ONLY that tab from index 0
5. setOverlay('menuOpen', false)
6. scrollPageTo(0)
```

Three facts about that shape drive every decision below.

**The outgoing tab is hidden before the incoming one is rendered.** Step 2
hides one container and reveals an empty one; step 4 fills it. Any transition
needs the reverse: the incoming tab rendered while still off screen, the
outgoing tab still visible, both laid out at once.

**Nothing has ever rendered an inactive tab.** `filterAndSortMedia()` reads
`.tab.active` and takes no argument, and `loadMedia()` calls it once for the
active tab only. So `#tvshows-content` holds an empty `.media-grid` *and a
visible `.loading` spinner* from first paint — `displayMedia()` hides the
spinner only for the tab it renders. Revealing the incoming tab early does not
show blank rows on the first switch; it shows a spinner.

**Both tabs scroll as one document.** They are siblings in `.container` and the
document is the scroller, so two grids on screen at once necessarily share one
`scrollY`. Step 6 then changes that shared value. This is the constraint the
whole design turns on.

There is also a rule that lies. `.content` declares
`opacity: 0; transform: translateY(10px); transition: …` with `.content.active`
setting the end state — an animation that has never once run, because a
`display: none` → `display: block` swap does not transition. It reads as though
the tabs already animate.

## Goals / Non-Goals

**Goals:**

- A committed swipe moves the outgoing grid off screen in the direction of the
  gesture, with the incoming grid arriving from the opposite edge.
- One continuous movement — the scroll reset is not visible as its own motion.
- The incoming tab is fully rendered, spinner resolved, before any of it shows.
- The resulting state is correct whether or not the animation runs or finishes.
- Cost bounded by the viewport, not by library size.

**Non-Goals:**

- **A finger-following drag.** The gesture stays discrete and fires once on
  commit. Tracking the touch would have to arbitrate against vertical scroll,
  `touch-action` and the overlay drag system, and is a separate change if ever.
- **Animating pointer tab clicks.** Desktop keeps the instant cut.
- **Per-tab scroll memory.** Returning to a tab still lands at its top, exactly
  as today.
- **Any change to the gesture's thresholds, angle test, or overlay guard.**

## Decisions

### Freeze the outgoing tab rather than reconcile two scroll offsets

The problem: a slide needs both grids on screen, both grids share one `scrollY`,
and the incoming one must show its top while the outgoing one shows wherever the
viewer was.

```
scrollY = 3000                       ┌──────────┬──────────┐
┌─ viewport ─┐   document scrolls    │ movies   │ tvshows  │  one track,
│ movies     │   as ONE box          │ @ row 47 │ @ row 47 │  one scrollY,
│ row 47     │                       └──────────┴──────────┘  wrong content
└────────────┘
```

The resolution is to take the outgoing tab out of the scroller. Pinned with
`position: fixed` and offset by the current `scrollY`, it renders pixel-
identical to where it already was but no longer responds to scrolling. The page
can then be set to 0 while nothing on screen reflects it:

```
1. freeze outgoing   position: fixed, offset by -scrollY
                     → looks identical, no longer follows scroll
                     → set styles, read NO geometry back (see measured, below)
2. scrollPageTo(0)   invisible: outgoing is detached from it,
                     incoming is not on screen yet          ← the trick
3. render incoming   filterAndSortMedia(incoming), still translateX(100%)
4. animate           outgoing → translateX(∓100%)
                     incoming → translateX(0)
5. teardown          outgoing display:none + static, incoming transform cleared
```

The scroll reset still happens; it happens in the one frame nothing depends on
it. That is what makes the movement single and continuous.

**Alternatives considered.**

| | Approach | Rejected because |
| --- | --- | --- |
| A | Instant `scrollTo(0)`, then slide two in-flow grids | Two motions for one gesture. Swiping from mid-list snaps to the top and *then* slides; the snap is the part the viewer notices, and it reads as a bug |
| C | Make `.content`'s existing fade actually run | Not a slide, and it still has to scroll to top underneath. Retained as the documented fallback if the measurement gate below fails |
| D | Per-tab scroll memory | Does not help: it is still one scroller, so it changes which wrong offset the incoming tab shows |

### Measured: the transform composites, and the proposed bound is worthless

Run against 7,000 movies / 1,200 shows in the dev image, real Chromium over
CDP, `translateX` over 600ms so steady state is legible.

| Viewport | Frozen tab | Steady-state median | Worst | Frames > 20ms |
| --- | --- | --- | --- | --- |
| 390×844 | bounded to 100vh (844px) | 16.7ms (59.9fps) | 16.8ms | 0 / 36 |
| 390×844 | **unbounded (1,228,722px)** | **16.7ms (59.9fps)** | **16.8ms** | **0 / 37** |
| 1280×900 | bounded to 100vh (900px) | 16.7ms (59.9fps) | 16.8ms | 0 / 36 |
| 1280×900 | **unbounded (618,103px)** | **16.7ms (59.9fps)** | **16.8ms** | **0 / 37** |

Baseline for comparison: 1,297 nodes, 59.9fps idle, document 1,227,442px tall.

**Go for the slide.** Transforming a box 1.2 million pixels tall does not cost a
single frame. The layer size is not the axis that matters — the compositor
rasterises what is near the viewport and translating the layer is not a repaint.

**And the `height: 100vh; overflow: hidden` bound is dropped.** It was proposed
as the mitigation for this risk, and measurement says it mitigates nothing:

- *Frame rate* — identical to the tenth of a millisecond, bounded or not.
- *Scrollable overflow* — identical. Freezing collapses `scrollHeight` from
  1,227,442px to 834px either way, because a fixed element contributes no
  scrollable overflow whether it is 844px tall or 1.2M. `scrollTo(5000)` lands
  at 0 in both cases.

Keeping it would mean carrying two extra properties to set and tear down, on the
strength of a hazard that was hypothesised and then measured away. It goes.

### Measured: never force layout during the freeze

The one visible cost in the whole sequence, and it is entirely avoidable.

| Freeze step | Cost |
| --- | --- |
| Setting `position: fixed` + offset | **0.2–0.4ms** |
| Reading `getBoundingClientRect()` back afterwards | **77.7ms** |

The first pass showed an 83–117ms opening frame and it looked like the transform
failing to composite. It was not: it was the forced synchronous layout from
reading the element's box back after taking it out of flow — instrumentation
that existed only to report the box size. Without the read-back the freeze costs
essentially nothing and the animation opens clean.

So: the freeze sets styles and reads nothing. Any later change that reads a
geometry — an `offsetHeight`, a `getBoundingClientRect`, a `getComputedStyle` of
a layout property — between taking the tab out of flow and starting the
transition reintroduces a ~78ms hitch on the first frame of every swipe. It will
present as "the animation is janky" and the transform will be blamed.

### Measured: the render lands on the slide's opening frame unless separated

The design predicted this as a risk and it turned out to be the largest one.
The incoming tab's window is built synchronously in the handler, but a rAF
callback runs *before* that frame's layout and paint — so starting the transform
in the first callback puts the cost of laying out a fresh 120-card grid on the
animation's opening frame.

| | Opening frame of the slide |
| --- | --- |
| One rAF, entrance fade on, no `will-change` | **183.4ms** of a 280ms slide |
| Two rAFs | 83.3ms |
| Two rAFs + no card entrance fade + `will-change` on setup | **16.7–33.4ms** |

Every frame *after* the first was a clean 16.7ms in all three cases. The slide
was never slow; two thirds of it was simply over before it became visible, which
reads as a jump.

Three changes, each earning its place:

- **Two rAFs, not one.** The second is load-bearing and the extra frame is
  invisible: the incoming tab is parked a viewport to the side and the outgoing
  one has not moved, so nothing on screen has changed yet.
- **No card entrance fade for a tab arriving on a slide.** The stagger exists to
  soften a grid appearing *in place*; a tab crossing the viewport as one object
  is already a soft arrival. It was also the most expensive thing on the frame —
  120 inline transitions and 120 rAF closures, doubled on a tab's first render.
- **`will-change: transform` on the frozen/parked state, not on `.tab-sliding`.**
  Declaring it alongside the transform pays for layer promotion exactly where
  the animation can least afford it.

### Measured: ~120ms between the gesture and the slide, and it is not ours

| Switch | `switchTab()` synchronous | Gesture → slide start | Frames > 20ms in the slide |
| --- | --- | --- | --- |
| First (tab never rendered — two windows) | 91.4ms | 122.2ms | 2 of 12 |
| Second (tab already rendered — one window) | 86.6ms | 120.0ms | **0 of 14** |
| Third | 89.4ms | 125.5ms | 1 of 13 |

Worth stating plainly because it is the one number that could be read as a
defect in this change: it is flat across the first, second and third switch, so
it is **not** the two-window first render. It is the per-switch filter, sort and
render of a 7,000-item library — work the instant path has always done and still
does. The animation did not add it; it gave it somewhere to be visible.

Reducing it means touching sort/filter/genre-UI cost, which belongs to
`sorting` and `genre-filter` rather than here. Left alone deliberately.

### Measured: the slide interpolates, and travels with the finger

Sampled every frame across the transition:

| Direction | Outgoing X | Incoming X | Distinct values |
| --- | --- | --- | --- |
| Swipe left → TV | 0 → **−379.5** | 360 → 0.4 | 17 |
| Swipe right → Movies | 0 → **+379.5** | −360 → −0.4 | 17 |

Recorded because the obvious check does not check this. An assertion that
`transform !== 'none'` passes against the *start* value, so it holds just as
well for an overlay that never moves — and it did, in the first version of this
verification. Movement does not begin until ~85ms after `.tab-sliding` lands, so
a probe sampling two or three frames in reads the start value and reports a
stationary slide. Sample the path, not a point.

### Measured: horizontal overflow containment is required

Confirmed rather than assumed. With the incoming tab at `translateX(100%)`,
`scrollWidth` goes to 750px against a 390px `clientWidth`. The containment in
the CSS task is load-bearing, and it must not outlive the transition.

### `filterAndSortMedia(type)` takes the tab as an argument

Step 3 of the sequence renders a tab that is not yet active, so reading
`.tab.active` is no longer sufficient. The parameter defaults to the active tab
so all five existing call sites keep today's behavior verbatim; only the
transition passes something else.

`displayMedia()` already takes a type and needs no change.

### Translate on the horizontal axis only

`firstVisibleRow()` derives the window's first row from
`view.grid.getBoundingClientRect().top + window.scrollY`. A `translateY` on an
ancestor moves that `top`, which corrupts the row arithmetic while the
transition runs — and a scroll event during the animation would re-window the
grid against it. `translateX` does not touch `.top`.

This is a constraint to state and pin, not a happy accident: a later "polish"
adding a slight vertical drift or a scale would reintroduce it silently, and it
would present as a windowing bug.

### Gate the animation on `isMobile`, the same flag that binds the gesture

`isMobile` already decides whether the swipe listeners are attached at all. The
transition sits inside the same condition rather than behind a media query.

The pairing rule is the point: this project has already shipped a hide-control
rule and its show-the-replacement rule as separate media queries that drifted to
992px and 768px, leaving every width between with neither. One condition cannot
drift from itself.

**Accepted consequence:** `isMobile` is a UA test *or* `innerWidth < 768`,
evaluated once at load. An iPad at 1024px matches the UA test and therefore
animates, while a 1024px desktop window does not. That is correct — it is a
touch device holding the gesture — but it is a decision, not an oversight.

### Resolve `.content`'s dead transition rather than leave it

Whatever the transition ends up being expressed as, the existing
`opacity`/`translateY` declarations on `.content` must not survive as a rule
that appears to animate the tabs and does not. `CLAUDE.md` states this directly:
a rule that appears to set an element's behavior must set it, because dead
declarations are where the next live one hides. Either the transition is
expressed there and works, or those declarations go.

### State the transition's duration and easing as tokens, read from `tokens.css`

Consistent with the z-ladder rule — chrome never restates a number. The
transition inherits the app-wide `prefers-reduced-motion` block in
`web/assets/tokens.css` for free, which collapses the duration to 0.01ms rather
than removing the transition, so any `transitionend` the teardown depends on
still fires.

### Teardown is idempotent and does not depend on `transitionend` alone

The spec requires the resulting state to be correct whether or not the
animation completes. A second swipe mid-flight, or a `transitionend` that never
arrives, must not leave a tab pinned, transformed or height-capped. The teardown
runs from a single function that is safe to call twice and is invoked both by
the transition ending and by a new transition starting.

## Risks / Trade-offs

**[The transform may not composite at library scale]** → **Resolved by
measurement — see above. This risk does not exist.** A `translateX` on a
1,228,722px box holds 59.9fps with zero dropped frames. Recorded here rather
than deleted because the hypothesis was reasonable and the next person to look
at a 1.2M-px transform will have it again.

**[A forced layout during the freeze costs ~78ms on the first frame]** → This is
the risk that turned out to be real, and it replaced the one above. Taking the
outgoing tab out of flow is free; *reading its geometry back* after doing so is
not. The freeze must set styles and read nothing. See the measured table above.

**[A transition cannot be verified by the tooling that verifies everything else]**
→ `make test` has no browser, and `chromium --headless --virtual-time-budget
--dump-dom` is worse than useless here: `requestAnimationFrame` never fires
under it, so a driver that cannot run rAF cannot observe a transition at all.
Five bugs have already reached the user through that gap while both the suite
and the browser check reported everything fine. Verification is `tools/browser.py`
driving a real Chromium over CDP — already committed, do not rebuild it — with
the Python test pinning only the source decisions, in the style of
`tests/test_grid_windowing.py`.

**[`position: fixed` interacts with `backdrop-filter` ancestors]** → An ancestor
with `backdrop-filter` becomes a containing block for fixed descendants, which
is exactly why the Actions tray is teleported to `<body>`. `.content` sits in
`.container`, not in the header, so this should not apply — but it is silent
when it does bite, and it is the first thing to check if the frozen tab renders
in the wrong place or the wrong size.

**[The horizontal translate opens a horizontal scrollbar]** → Confirmed by
measurement: `scrollWidth` 750px against a 390px `clientWidth`. Overflow must be
contained for the transition's duration, and the containment removed on teardown
so it cannot outlive the animation.

**[The `.swipe-indicator` toast may become redundant]** → It currently announces
"Switched to TV Shows" after a commit, which is a caption for a transition that
did not exist. With visible directional motion it may be noise. **This is not
decided here** — it is a product call, listed as an open question, and the
change ships with the toast unchanged unless the user says otherwise.

**[A first switch renders 120 cards mid-gesture]** → The incoming tab's render
happens between the freeze and the animation. At the window size of 120 items
that is bounded and independent of library size, but it is real work on the
frame the animation starts. Measure it; if it lands badly, rendering the
incoming tab one frame earlier is the lever.

## Open Questions

- **Does the `.swipe-indicator` toast stay?** Ships unchanged by default.
- **Duration.** The overlay trays use 280ms. Matching them is the obvious
  default and keeps the app's motion consistent; confirm against the real thing
  rather than picking a number here.
- **Should the first switch pre-render the inactive tab at load instead?** It
  would remove the spinner problem at its source rather than sequencing around
  it, at the cost of one extra windowed render during boot. Deferred: the
  sequencing is required regardless, and this is an optimisation on top of it.
