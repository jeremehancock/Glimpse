## Context

`animate-tab-transition` shipped a slide that plays *after* the gesture
resolves. Its design named a finger-following drag as an explicit Non-Goal:

> Tracking the touch would have to arbitrate against vertical scroll,
> `touch-action` and the overlay drag system, and is a separate change if ever.

This is that change. Everything that design measured still holds and is not
re-litigated here — the transform is free at library scale, a forced layout
during the freeze costs 77.7ms, the render must be separated from the slide's
opening frame by two rAFs, and the translate must not move the grid's measured
top. What changes is *when* the sequence starts and what drives it in between.

Today's sequence, all of it inside `touchend`:

```
touchend ─▶ handleSwipe() ─▶ switchTab() ─▶ switchTabAnimated()
                                             │
                                             ├─ read scrollY
                                             ├─ applyTabState()      ~90ms at
                                             ├─ filterAndSortMedia() ─ 7,000 items
                                             ├─ freeze outgoing, park incoming
                                             ├─ scrollPageTo(0, 'instant')
                                             ├─ move .active
                                             └─ rAF ▸ rAF ▸ set --tab-shift
```

Four facts about the current code drive every decision below.

**The setup is one synchronous block and it is expensive.** The measured
~120ms between gesture and slide is filter, sort and genre reconciliation over
the whole library — flat across the first, second and third switch, so it is not
first-render cost. Today it lands in the dead air after a finger lifts. A drag
has to run it while the thumb is on the glass.

**`touchmove` claims the gesture 100px late.** The current handler calls
`preventDefault()` only once horizontal travel exceeds `swipeThreshold` (100).
On iOS, a touch sequence whose first moves were not cancelled has already been
handed to the scroller, and later `preventDefault()` calls against it are
ignored. The current code gets away with this because it never needs to move
anything — it only needs to read the endpoints.

**The freeze is what makes two grids showable at once,** and it works because
`position: fixed` renders the outgoing tab identically while removing it from
the scroller. Measured previously: freezing collapses `scrollHeight` from
1,227,442px to 834px, so the browser clamps `scrollY` to 0 on its own.

**`firstVisibleRow()` reads `grid.getBoundingClientRect().top`.** It is the sole
input to which rows the grid renders, and it is reached only from the `scroll`
and `resize` handlers and from a fresh render. This is why the existing rule is
horizontal-translate-only.

## Goals / Non-Goals

**Goals:**

- The tabs move with the thumb, every frame, at a fixed relationship to it.
- The gesture is abandonable: dragging back or lifting short returns to rest,
  with the tab unchanged.
- A tactile lift at thumb-down — the moving tab reads as a card lifted off the
  page rather than a page being repainted.
- Commit reflects intent: a long drag or a fast flick, not one fixed distance.
- The ends of the tab list resist rather than silently doing nothing.
- Every guarantee the shipped transition makes survives: nothing visible before
  it is rendered, no separate scroll motion, correct state regardless of the
  animation, one gate shared with the gesture.

**Non-Goals:**

- **Pointer drag on desktop.** A tab click stays an instant cut.
- **Per-tab scroll memory.** Returning to a tab still lands at its top.
- **A third tab, or wrap-around.** Two tabs, and the ends are ends.
- **Reworking filter/sort cost.** Named as a lever below and gated by
  measurement, but it belongs to `sorting` and `genre-filter`.
- **Generalising this into the overlay drag system.** `overlays.js` owns a
  vertical dismissal on a `.sheet`; this is a horizontal drag on the page
  behind every overlay. Sharing them would mean one gesture arbitrating two
  axes across two ownership boundaries.

## Decisions

### The gesture has four phases, and the expensive one is the second

```
touchstart          record origin. Claim nothing. Do no work.
   │                A tap and a vertical scroll must both still be free.
   ▼
touchmove #1..n     AXIS LOCK at 8px of travel, then one of:
   │                  vertical   → release the gesture forever, stay passive
   │                  horizontal → preventDefault from here on, and SET UP
   │                               (the ~90ms lands here, once)
   ▼
touchmove #n+1..    TRACK. Per frame: write two transforms. Read nothing.
   │
   ▼
touchend            SETTLE. Commit or abandon; hand off to the existing
                    transition machinery, which is unchanged.
```

**Why the lock is at 8px and not at the 100px threshold it replaces.** The lock
is where `preventDefault()` starts, and on iOS a sequence already given to the
scroller cannot be taken back. 8px is small enough to precede a scroll and large
enough that a tap's jitter does not trip it. The 100px number does not disappear
— it becomes part of the *commit* test, where it always belonged.

**Why the axis is decided once and never revisited.** A gesture that re-arbitrates
mid-drag is a gesture that can hand a moving page back to the scroller halfway
through. Once vertical, the touch is the scroller's until it ends; once
horizontal, it is the tab's.

### Setup runs at axis lock, and the incoming tab is already warm when it gets there

This was the change's central risk. It was gated on a measurement, the gate was
run before any tracking code was written, and **it failed — against a cost model
that turned out to be wrong.** Both halves are recorded because the wrong model
is the more useful artifact.

The setup must run before the first tracked frame: the incoming tab has to be
rendered and parked before it can be moved. Axis lock is the earliest moment we
know the gesture is ours and the latest moment the setup can complete without a
visible stall.

**Measured, 7,000 movies / 1,200 shows, 390x844.** Headless Chromium on the
machine used here runs 2.5x the figures in the archived transition's design —
established by re-running that design's own `switchTab()` measurement, 221.4ms
here against its ~89ms — so both columns are given.

| | Here | Scaled |
| --- | --- | --- |
| Setup block (`applyTabState` + `filterAndSortMedia`) | 175.3ms | ~70ms |
| — filter + sort | 16.9ms | ~7ms |
| — `displayMedia()` | 147.9ms | **~59ms** |
| `buildCard()` x120, in isolation | 45.9ms | ~18ms |
| `measureGrid()` when it forces layout | 48.1ms | ~19ms |

**The cost is not the library.** It is building 120 cards and the forced layout
that follows, and it is the same at 1,200 items as at 7,000. The gate's named
lever — memoising the filtered-and-sorted list — addresses 16.9ms of 175.3ms.
It would have removed a tenth of the cost and left the gate failing, and it
would have looked like a fix until someone re-measured.

Worth stating plainly, because it is the reusable part: *the setup was assumed
expensive because the library is large, and the library's size is not a term in
it.* A tab's first render pays twice over — `displayMedia()` re-measures and
re-renders once a real card exists to measure from — so the first switch is
~180ms here, and that is the worst case rather than the 7,000-item case.

**The lever that works is not rendering at all.**

| | Here |
| --- | --- |
| Re-rendering a tab that already shows the right thing | 142.9ms |
| Comparing a render signature instead | **0.1ms** |

Each tab keeps its own view in `gridViews`, including whatever it last rendered.
If the search term, genre, sort order and underlying data are unchanged since
then, the tab's DOM is already correct and rendering it again produces the same
nodes. So the setup carries a **render signature** — the tuple that fully
determines what a window shows — and skips the render when it matches.

That alone leaves two cases still paying: the first drag of a session, where the
inactive tab has never rendered, and the first drag after a search or sort
change, which invalidates it. Both are closed by **re-warming the inactive tab
at idle** whenever the selection changes, so the signature already matches by the
time a thumb arrives.

**Alternative B below was rejected on reasoning that only holds for pre-rendering
once at boot.** It is right that a boot-time render cannot anticipate a search
the viewer has not typed yet. It is wrong about re-warming on *change*, which
tracks the selection by construction — and which only becomes expressible once
the signature exists to say whether a warm tab is still warm. The signature and
the re-warm are one mechanism; neither is worth much alone.

**The skip must be conservative in one direction only.** A signature that
wrongly reports "stale" costs a render nobody needed. A signature that wrongly
reports "current" shows the viewer a grid that does not match their search, and
this application's oldest failure mode is a wrong library that looks like a
working one. Anything not provably in the tuple is grounds to re-render.

Alternatives considered and rejected:

| | Approach | Rejected because |
| --- | --- | --- |
| A | Set up at `touchstart` | Every tap and every vertical scroll pays it. Taps would feel laggy and scrolls would start late — a far larger surface than the drag. |
| B | ~~Pre-render the inactive tab at idle after boot~~ | **Partly adopted.** The objection — that a render must reflect the current search, genre and sort, which change after boot — defeats a one-time boot render and not a re-warm driven by those changes. Adopted in that form, paired with the signature. |
| C | Start tracking with the outgoing tab alone, swap the incoming in when ready | The viewer drags a page aside and sees a gap where the next one should be. Worse than a stall. |
| D | Move the setup off the main thread | There is no worker, no build step, and the work is DOM construction. Not available. |
| E | Make `buildCard()` cheaper — clone a template instead of parsing `innerHTML` per card | Attacks 45.9ms of the 147.9ms and helps every render in the app, not only the drag. Declined *here* because it touches the grid's hot path, which `media-browsing`'s windowing requirements cover, and because not rendering beats rendering faster. It is the right change on its own terms and belongs in its own. |

### Both tabs are fixed for the drag's duration, and the scroll reset moves to the settle

The shipped transition freezes the outgoing tab and immediately sets the page to
0, because the incoming tab is in flow and must show its own top. During a drag
that is wrong: the gesture can be abandoned, and a page already reset to 0 has
thrown away the position it must return to.

So the drag freezes **both**:

```
setup:     outgoing  position: fixed; top: -y      renders identically
           incoming  position: fixed; top: 0       shows its own top
                     (browser clamps scrollY to 0 on its own — the document
                      has collapsed to viewport height)

track:     transform on both. Document scroll is irrelevant; it cannot move.

settle ─┬─ COMMIT   slide to ±100% / 0, then unfreeze incoming with the
        │           page already at 0 → pixel-identical, no reset needed
        │
        └─ ABANDON  slide back to rest, then unfreeze outgoing and restore
                    scrollY to the captured y in the SAME synchronous block
```

The abandon path is the one that needs care. Removing `position: fixed` puts
the tab back in flow at `scrollY === 0` — the top of the library — and only then
can the scroll be restored. Both happen in one synchronous block with no paint
between them, so there is no flash. It does force a layout, which is the 77.7ms
hazard from the shipped design — but it lands *after* the settle animation has
finished, on a frame where nothing is moving, which is the only place in this
design that cost is affordable. **Deliberate placement, not an oversight.**

Pinning both does make the browser clamp `scrollY` to 0 by itself: a fixed
element contributes no scrollable overflow, so the document collapses to
viewport height. It is tempting to conclude the explicit
`scrollPageTo(0, 'instant')` is now redundant, and that conclusion is wrong in
the way this project is usually wrong. Clamping is something the browser does
as a consequence of the collapsed document, not something the app asked for —
and if it ever does not happen, the incoming tab arrives at the outgoing tab's
scroll offset, which is exactly the failure the freeze exists to prevent. The
call stays. It costs nothing when it is a no-op, and it is the difference
between an instruction and an assumption.

### The window does not move while the tabs do

The lift is a scale. A scale changes `getBoundingClientRect().top` for every
card, which is `firstVisibleRow()`'s only input. The shipped rule — horizontal
translate only — exists precisely to prevent that.

**The rule is not being weakened; its precondition is being stated and
enforced.** `updateGridWindow()` returns early while a tab drag is live, so no
re-window can be computed against a transformed rect. That guard is the reason
a scale is admissible, and the two arrive together or neither does.

Two supporting facts, both worth stating because each alone looks like the whole
answer and is not:

- Re-windowing is reached only from the `scroll` and `resize` handlers. While
  both tabs are fixed the document cannot scroll, so no scroll event can fire.
  **This is a consequence of the freeze, not a property of the lift.** Pairing
  a safety with a mechanism that happens to imply it is exactly how this repo
  shipped a 992px rule and a 768px rule that were supposed to be one condition.
  The guard is explicit for that reason.
- The **sliding** transform stays horizontal-only. `--tab-shift` has no Y
  equivalent and gains none. The scale is a separate, short-lived component of
  the same `transform`, applied at lock and removed at teardown, and it is the
  guard that makes it safe rather than its size.

Alternative considered: express the lift with `box-shadow`, `border-radius` and
a scrim only, changing no geometry. It is genuinely safer and needs no guard.
Rejected because the scale is what makes the effect read as a card rather than
a shadow, and because the guard is worth having on its own — a re-window
computed mid-gesture would be a defect whether or not a scale caused it.

### The tabs move edge to edge. Parallax was tried and reverted

```
finger travels 100px left

  outgoing   translateX(-100px)          1.0x, from 0
  incoming   translateX(+290px)          1.0x, from +100vw
```

Both tabs track the finger at the same rate, one viewport apart, so the pair
moves as a single strip. One leaves exactly as fast as the other arrives.

**The first version did the platform-standard thing and it was wrong here.** The
incoming tab parked a third of a viewport out and travelled at a third of the
finger's speed — the iOS push/pop parallax, chosen deliberately over a locked
1:1 because it reads as layered rather than flat.

At a third of a viewport the two grids **overlap for the entire gesture**. That
is not a side effect of the parallax, it is what the parallax IS: the incoming
view slides in over the outgoing one. Which of the two is drawn on top then has
to be decided, and nothing decided it — both tabs carry the same `z-index` (they
need it to clear the drag scrim), so paint order fell back to document order.
`#tvshows-content` comes second in the markup, so **TV Shows painted over Movies
in both directions**.

Reported as *"the TV show grid is always on top"*, which is precisely accurate
and sounds like a z-index bug. It is a geometry decision: at a full viewport
apart the question cannot arise at all.

Fixing the z-order instead was possible — rank the incoming tab above the
outgoing one — but it keeps a gesture in which one grid obscures another the
viewer is still dragging, and "side by side, one going away and the other
replacing it" is what was actually wanted.

Two consequences worth recording:

- **The horizontal overflow is back to its full measured extent.** 750px against
  a 390px `clientWidth`; the parallax had halved it. The containment was always
  required and is unchanged.
- **The lift now does a second job.** At `scale(0.94)` each tab is ~23px
  narrower than the viewport, so a gap opens between them and the pair reads as
  two cards rather than one continuous sheet. That is the layered quality the
  parallax was chosen for, obtained without the overlap.

There is no ratio token any more. Pinned at 1 it would be a knob that does
nothing, and this project treats a declaration that appears to control something
and does not as worse than none.

### Commit is distance OR velocity, and rest is the third outcome

| Outcome | Test at `touchend` |
| --- | --- |
| **Commit** | travelled ≥ ⅓ of the viewport width, **or** velocity over the last few moves exceeds the flick floor |
| **Abandon** | anything else, including a drag that went out past ⅓ and came back |
| **No-op** | the axis never locked — this was a tap or a scroll |

Velocity is measured from the last two or three `touchmove` samples, not from
the whole gesture: a slow drag ending in a flick is a flick, and averaging over
the full duration erases exactly the intent the test is for.

A drag that has passed the distance threshold is **not** latched. The viewer can
drag back and abandon. Latching would mean the page keeps following a finger
whose gesture has already been decided, which is the thing this change is
removing.

### The settle is timed from what is left to travel, floored

A fixed 280ms is wrong at both ends: a tab released at 90% of its travel spends
280ms crossing the last sliver, and one released at 5% covers nearly the whole
viewport in the same time. The settle's duration scales with the remaining
distance, clamped to a floor so a near-complete drag still resolves visibly
rather than snapping.

`--dur-tab` is retained as the **maximum** — a settle from rest travels the same
distance in the same time as today's transition, so a committed swipe that
barely moved looks exactly like the shipped animation. That is the continuity
argument for keeping the token rather than introducing a second one.

### Reduced motion keeps the follow and collapses the settle

A drag is direct manipulation. The viewer is moving the page with their own
thumb, and the page is where they put it — there is no animation to reduce and
suppressing the follow would make the gesture unusable rather than calmer.

What reduced motion governs is the **settle**, which is the only part the app
plays on its own. The app-wide rule in `tokens.css` already collapses transition
durations to 0.01ms, so the settle resolves on the next frame and the
`transitionend` the teardown listens for still fires. Nothing new is needed;
what is needed is a spec sentence saying this is the intended reading, so the
follow is not "fixed" later by someone applying the reduced-motion rule to it.

The lift's scale is part of the same collapse: under reduced motion it lands
instantly rather than easing in.

### Tracking writes and never reads

The per-frame handler sets two CSS custom properties and nothing else. No
`getBoundingClientRect`, no `offsetWidth`, no `getComputedStyle` — the same ban
the shipped freeze carries, extended to every frame of the drag, where its cost
would be paid 60 times instead of once.

Everything the tracker needs is captured at lock: the viewport width, the origin
X, the scroll offset. The viewport cannot change mid-gesture without a resize,
and a resize mid-drag ends the drag.

`touchmove` fires at the touch sampling rate, which may exceed the frame rate.
The handler coalesces to one write per rAF so a 120Hz digitiser cannot schedule
two style writes per frame.

### The gesture is refused, not aborted, when an overlay is open

The existing guard checks `isOverlayOpen('detailOpen')` inside `handleSwipe()` —
after the fact, which is sufficient when nothing has moved. A drag has to refuse
*before* claiming the axis, because by the time it could abort it has already
called `preventDefault()` and set up two frozen tabs.

The check moves to `touchstart`, and widens: any open overlay, plus any touch
whose target lies inside an overlay panel. An overlay's own drag belongs to
`overlays.js` and a touch on a backdrop belongs to the overlay it dismisses.

### Teardown stays one idempotent function, and now has more to clear

`endTabTransition()` already exists, is safe to call twice, and runs from both
`transitionend` and a timer. It grows the drag's state: the incoming tab's
freeze, the lift, the scrim, the window guard, the coalescing rAF handle, and
the abandon path's scroll restore.

Every entry point calls it first: a new gesture, a tab click, a resize, a
`touchcancel`. `touchcancel` matters more here than it did for a discrete
gesture — an incoming call or a system gesture mid-drag must not leave two tabs
pinned and the grid's window frozen.

## Risks / Trade-offs

**[The setup lands on the drag's first frame]** → **Was real, measured at ~70ms
scaled, and resolved — but by a different lever than the one predicted.** The
render signature takes it to 0.1ms when the incoming tab is warm, and the idle
re-warm keeps it warm. See the decision above. The residual risk is that the
signature is wrong rather than that the render is slow, which is why it errs
toward re-rendering.

**[The render signature reports a stale tab as current]** → The viewer drags to
a grid that does not match their search or sort. This is the failure this
project cares most about — a wrong library indistinguishable from a working one
— and it is silent. Mitigated by making the tuple total rather than clever: any
input to what a window shows is in it, and anything that cannot be proven to be
in it is grounds to re-render. Cheaper to render 120 cards nobody needed than to
show the wrong 120.

**[iOS hands the touch to the scroller before the axis locks]** → 8px lock with
`preventDefault()` from that move onward, and the listener non-passive from the
start. If a scroll still steals it, the fallback is `touch-action: pan-y` on
`.container`, which tells the browser up front that horizontal is ours. Not the
default because it changes the browser's handling for every touch on the
container, including ones this gesture never claims.

**[A scale re-windows the grid mid-drag]** → The explicit `updateGridWindow()`
guard, not the incidental fact that fixed tabs cannot scroll. Stated above at
length because the incidental fact is the tempting answer.

**[A scale about the default origin throws the grid off the screen]** →
**NOT PREDICTED. Shipped to `:dev` and found by the user.** The entry above
treats a moved `getBoundingClientRect().top` purely as an arithmetic hazard for
the windowing, and guards it correctly. It is also a *visible* hazard, and that
half was never considered.

`transform-origin` defaults to the element's own centre. A tab holding 7,000
items is 1,227,442px tall, so its centre is ~600,000px below the viewport, and
scaling by 0.94 about a point that far away moves the top edge down by
`height × 0.03`. **Measured: the first card jumped +36,791px.** The grid left
the screen downward the instant a thumb touched it.

The second symptom is the more instructive one. The displacement is proportional
to library size, so the 7,000-item tab vanished while the 1,200-item tab barely
moved — and it presented as *"it always shows the TV Shows grid whichever way I
swipe."* That is a routing bug, it does not exist, and it is where anyone would
look first. Two reports, one cause, and the plausible cause was the wrong one.

Fixed by `pinTab()`, which sets `transform-origin` to the viewport's centre in
the element's own coordinates, so the tab shrinks around the part of it the
viewer can actually see. The residual shift of the top row is 20px at a 0.94
scale — that is the lift, symmetric about the viewport centre, and it resolves
to zero on settle.

**The general lesson, which is why this is written up rather than just fixed:**
these panels are *enormous*, and that fact has to be the first thing in mind
when reasoning about them, not a footnote. The archived design already knew it
(*"a `translateX` on a box 1,228,722px tall"*) and drew the correct conclusion
for translation, where size genuinely does not matter. For a scale it decides
everything.

**[The frozen tabs sit under the header]** → Also missed initially and fixed in
the same pass. `.content` begins below the header, so pinning at `-scrollY`
puts the grid that far too high. The offset must come from the tab's own
position, which is not a constant — the header shrinks on scroll. That needs one
`getBoundingClientRect()`, taken **before any write** in the setup, against
layout the browser has already computed. The ~78ms rule is *never measure what
you just invalidated*, not *never measure*, and the test now enforces the
ordering rather than banning the call.

**[The abandon path forces a layout]** → Confirmed hazard, ~78ms, placed
deliberately after the settle rather than avoided. If it proves visible, the
lever is restoring the scroll before removing `position: fixed` and accepting
one frame of clamping — measure before choosing.

**[Two fixed tabs interact with a `backdrop-filter` ancestor]** → An ancestor
with `backdrop-filter` becomes a containing block for fixed descendants, which
is why the Actions tray is teleported to `<body>`. `.content` sits in
`.container`, not the header, and the shipped transition already freezes one tab
there without issue. Second one, same parent, same answer — but it is silent
when it bites, and it is the first thing to check if a tab renders at the wrong
size.

**[The drag competes with the overlay drag system]** → Refused at `touchstart`
rather than arbitrated. Two gesture systems on two axes with two owners is the
shape that produces a gesture belonging to neither.

**[This cannot be verified by `make test`]** → Unchanged from the shipped
transition and worth restating, because a drag is harder: CI has no browser, and
`chromium --headless --virtual-time-budget` fires no `requestAnimationFrame`, so
a driver using it reports a stationary page as a passing one. Verification is
`tools/browser.py` over CDP with `Input.dispatchTouchEvent`, sampling the
transform across frames. **Sample the path, not a point** —
`transform !== 'none'` is satisfied by the start value and has already produced
a false pass in this repo once.

**[The follow could be verified against the wrong thing]** → A drag's proof is
that the transform *corresponds to the finger*, not merely that it changes.
**Measured against a known path, 390x844, 7,000 movies** — every value exact,
not approximate:

| Finger | Outgoing X | Incoming X | Scale |
| --- | --- | --- | --- |
| −30 | −30.0 | 118.8 | 0.94 |
| −70 | −70.0 | 105.6 | 0.94 |
| −120 | −120.0 | 89.1 | 0.94 |
| −70 *(reversed)* | **−70.0** | **105.6** | 0.94 |
| release (short) | 0 | 0 | 1 |

The incoming column is `128.7 + 0.33 × delta` to the tenth of a pixel, where
128.7 is `390 × 0.33`. The reversal row is the one that matters: a handler
tracking `abs(delta)` follows a finger perfectly outward and refuses to come
back, and it passes every non-reversing check.

Resist measured at exactly `0.25 ×` travel with the active tab unchanged;
abandon from 5,000px in a 1,227,442px document returned to 5,000px.

**[Measuring the gesture with a harness inside the frames it times]** → Not
predicted, hit anyway, and worth recording because the first number looked like
a real defect. Dispatching synthetic `TouchEvent`s from the same rAF callback
that recorded frame gaps reported a **33.4ms median**. The real CDP input path
on the same build reports **16.7ms**. It is the forced-layout trap wearing
different clothes: the cost of the measurement was inside the measurement.

A control is equally necessary. Each `browser.touch()` is a blocking websocket
round-trip, and dispatching the same sequence at a position where the gesture is
never claimed drops **53–67 frames per run on its own** — against the drag's
**56–60**. Median 16.7ms either way. So the honest statement is: *the drag holds
60fps at the median and its tail is indistinguishable from the driver's in this
environment.* The tail is a question for a real phone, which is where it was
always going to be answered.

**[Removing the first-load tip removes discoverability]** → ~~The tip taught a
gesture with no visible affordance. A drag has one: the page moves the moment
the thumb does.~~ **It was missed, and it is back.** A drag demonstrates itself
only to someone who already tries it; at rest the gesture still has no visible
affordance, so removing the one thing that announced it left it discoverable by
accident. The *post-commit* toast naming the arrived-at tab stays gone — the
motion states that, and the direction with it.

## Migration Plan

None. No data, no config, no compose surface, no persisted state. The change is
authored HTML/CSS/JS served as written; a rollback is a revert.

## Open Questions

All of these need a thumb, and none of them blocks the change. They are the
content of task 8.10.

- **The lift's exact scale.** 0.94 is the working number and it is a look, not
  a measurement. Confirm on a real phone against real artwork — a grid of
  posters shrinking reads differently from a plain surface.
- **Does the scrim dim the page or the outgoing tab?** They differ only when
  the incoming tab is partly on screen. Decide against the real thing.
- **Is the flick floor one number or two?** A flick toward the end of the list
  has nowhere to go and rubber-bands; whether the same velocity should feel
  different there is a judgement call best made with a thumb.
- **Should the settle's easing differ between commit and abandon?** An abandon
  is an undo and arguably wants the shorter `--ease-exit`. Ships with one easing
  unless the real thing disagrees.
- **Should the header's tab highlight follow the drag, or wait for the commit?**
  It follows today, because `applyTabState()` runs in the shared setup — the
  genre reconciliation has to happen before the incoming tab is rendered, and
  the highlight comes along with it. So a drag out and back flicks the highlight
  to the other tab and returns it. Arguably right (the header tracks the
  content) and arguably a flicker. Splitting `applyTabState()` into its data
  half and its visual half is the lever if the answer is "wait", and it is a
  small refactor rather than a redesign. Left as it is deliberately, not by
  omission.
