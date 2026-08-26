## 1. Measure before building

The design's central risk is that the ~90ms setup moves from the dead air after
a finger lifts to the first frame of a live gesture. This group decides the
shape of group 4 and must not be skipped.

- [x] 1.1 Seed a library to thousands with `tools/seed_library.py` and confirm the
      baseline still holds — the numbers in `test_tab_transition.py`'s docstring
      were measured before this change and are what group 8 compares against.
      *Done: 7,000 movies / 1,200 shows, 1,297 nodes. `switchTab()` synchronous
      median 221.4ms here against the archive's ~89ms, so this machine runs
      **2.5x** the archived figures and every number below is quoted both ways.*
- [x] 1.2 Add touch dispatch to `tools/browser.py`: `Input.dispatchTouchEvent`
      sequences (start / a path of moves / end and cancel) with per-frame
      sampling of `getComputedStyle(el).transform` on both tabs. Sample the path
      across frames, never a single point — `transform !== 'none'` is satisfied
      by the start value and has produced a false pass in this repo already.
      *Done: `Browser.touch()`, `Browser.drag()`, `Browser.frame_times()`.*
- [x] 1.3 Measure the current `switchTabAnimated()` setup block —
      `applyTabState()` plus `filterAndSortMedia()` — in isolation at library
      scale. Record the number.
      *Done: median **175.3ms** here (~70ms scaled), worst 301.4ms.*
- [x] 1.4 Apply the gate: within ~2 frames (≲33ms), proceed to group 2. Beyond
      it, do task 1.5 first and re-measure.
      *Applied. **The gate FAILS** — ~70ms scaled is about 4 frames, not 2.*
- [x] 1.5 ~~Memoise the filtered-and-sorted list per (tab, search term, genre,
      sort order).~~ **Superseded — the measurement says this is the wrong
      lever.** Filter + sort is 16.9ms of the 175ms (~7ms of ~70ms scaled).
      `displayMedia()` is 147.9ms of it, and it costs the same at 1,200 items as
      at 7,000 — it is not library-size work at all. Replaced by 1.6–1.8.
- [x] 1.6 Give each grid view a **render signature**: the tuple that fully
      determines what its window shows — tab, search term, genre, sort order and
      data length. Set it when `displayMedia()` renders. Make it total rather
      than clever: anything that can change what the grid shows belongs in it.
      *Done: `renderSignature()`. `JSON.stringify`, not a delimiter — search term
      and genre both admit spaces, so "a b"/"c" and "a"/"b c" join identically,
      which is a collision in the one direction this must never be wrong in.*
- [x] 1.7 Skip the render in `filterAndSortMedia()` when the signature matches
      and the view already holds cards. Comment the asymmetry — a false "stale"
      costs a render, a false "current" shows the wrong library — so the next
      person to optimise it knows which way it is allowed to be wrong.
      *Done. `view.rendered > 0` is required alongside the signature, and the
      no-results path zeroes it — that branch leaves `view.data` holding the
      previous selection, which the delegated click listener reads from.*
- [x] 1.8 Re-warm the inactive tab at idle whenever the selection changes, so a
      drag arrives at a tab whose signature already matches. Use
      `requestIdleCallback` with a `setTimeout` fallback, cancel a pending warm
      before scheduling another, and never warm while a drag is live.
      *Done: `warmInactiveTab()`, called only after a render actually happened —
      which is what terminates the recursion. Also added `tabDrag` and
      `tabGestureActive()`, the one predicate groups 3 and 4 both read.*
- [x] 1.9 Re-measure 1.3 with 1.6–1.8 in place. Record both numbers. The gate is
      the same: within ~2 frames scaled, proceed to group 2.
      *Done: **175.3ms → 1.4ms** here (~70ms → ~0.56ms scaled). **GATE PASSES.**
      Correctness re-checked in the same run: a search on one tab leaves the
      other showing results for the new term, and clearing it rebuilds.*

### Group 1 findings — measured 2026-08-25, 7,000 movies / 1,200 shows, 390x844

All figures are headless Chromium on this machine, which runs **2.5x** the
archived numbers; the scaled column is what the archive's machine would show.

| | Here | Scaled |
| --- | --- | --- |
| `switchTab()` synchronous, median | 221.4ms | ~89ms — matches the archive |
| Setup block (`applyTabState` + `filterAndSortMedia`) | 175.3ms | ~70ms |
| — filter + sort | 16.9ms | ~7ms |
| — `displayMedia()` | 147.9ms | ~59ms |
| `buildCard()` x120, in isolation | 45.9ms | ~18ms |
| `measureGrid()` when it forces layout | 48.1ms | ~19ms |
| Re-render a tab already showing the right thing | 142.9ms | ~57ms |
| Comparing a render signature instead | 0.1ms | 0.04ms |

**The cost is building 120 cards and the forced layout that follows, not the
library.** 1,200 items cost the same as 7,000. A tab's *first* render pays
twice — `displayMedia()` deliberately re-measures and re-renders once a card
exists to measure — so the first switch is ~180ms here / ~72ms scaled.

The design's Decision "Setup runs at axis lock" and its Alternative B
("Pre-render the inactive tab at idle — does not solve it") were both reasoned
against a cost model the measurement contradicts. **Both revised in `design.md`
before group 2 was started**, along with the risk they belonged to.

**Resolved by 1.6–1.8: 175.3ms → 1.4ms (~70ms → ~0.56ms scaled).**

Two environment notes for whoever runs this next, neither of them project bugs:

- **`make lint-js` needs Node 18+ on PATH.** With 16.20.1 it dies inside
  ESLint's config loader with `structuredClone is not defined`, which reads like
  a broken config rather than a stale runtime. `CLAUDE.md` already says 18+.
- **Do not bind-mount single files into the dev container.** An editor that
  writes-then-renames replaces the inode and the container keeps serving the old
  one — the page looks unchanged and the change reports as not working. Mount
  `/app/data` only and `docker cp` the web assets.

## 2. Tokens and CSS

- [x] 2.1 Add tokens to `web/assets/tokens.css`: the lift's scale, the parallax
      ratio, the scrim colour, the settle's minimum duration, and the flick
      velocity floor. Comment each with what it is and why it is a token —
      the parallax ratio in particular is read by two transforms that must not
      disagree. `--dur-tab` is retained as the settle's maximum.
- [x] 2.2 Extend `.content.tab-leaving` and `.content.tab-entering` so both
      pin with `position: fixed` — the incoming at `top: 0`, the outgoing at
      the inline offset it already takes. Keep `will-change: transform` on
      these setup states and off the sliding state.
- [x] 2.3 Compose the transform from separate custom properties for the
      horizontal offset and the lift's scale, so the tracker writes the offset
      each frame without restating the scale. Keep the offset horizontal —
      there is no Y equivalent and it gains none.
- [x] 2.4 Add the lift's presentation: elevation, corner radius, and the scrim
      behind the moving tab. All values read from tokens.
      *Done, minus the radius — **deliberately dropped, not forgotten.** The
      frozen tab is pinned at the captured offset and is as tall as the whole
      library, so its corners are never on screen; the declaration would have
      drawn nothing, and clipping cards to it would have meant `overflow:
      hidden` on the panel. Both files say so at the point someone would add it.
      The scrim sits below the tabs and below `--z-chrome`: `html::after` comes
      after `body`, so without an explicit z-index it would paint over the very
      tabs it exists to sit behind.*
- [x] 2.5 Give `.tab-sliding` a transition duration driven by a custom property
      the settle sets per release, rather than a fixed `--dur-tab`.
- [x] 2.6 Confirm `.tab-transitioning`'s `overflow-x: hidden` still covers the
      drag. The incoming tab now parks a third of a viewport out rather than a
      full one, so there is less overflow but still some.

## 3. The window guard

- [x] 3.1 Add a module-level flag set while a tab drag is live, and make
      `updateGridWindow()` return early when it is set. Comment it with why it
      is explicit rather than resting on frozen tabs receiving no scroll events.
- [x] 3.2 Make the resize handler resolve any live drag before re-measuring, so
      a resize mid-drag cannot re-window against a transformed rect.

## 4. Split the transition into setup / track / settle

- [x] 4.1 Extract the setup from `switchTabAnimated()` into a function that
      captures `scrollY`, runs `applyTabState()` and `filterAndSortMedia()`,
      freezes **both** tabs, applies the lift, parks the incoming tab at the
      parallax offset, and sets the window guard. It reads no geometry after
      the freeze — the shipped 77.7ms hazard is unchanged.
- [x] 4.2 Write the tracker: given the touch's current X, write the two
      horizontal offsets — outgoing at 1:1, incoming interpolated by the
      parallax ratio. Coalesce to one write per `requestAnimationFrame` so a
      high-rate digitiser cannot schedule two style writes per frame. It reads
      nothing.
- [x] 4.3 Add damping to the tracker for a drag toward a tab that does not
      exist, and make that case skip the incoming tab's setup entirely — there
      is nothing to render or park.
- [x] 4.4 Write the commit settle: transition both offsets to their end values
      over a duration scaled from the distance remaining, floored by the token
      and capped at `--dur-tab`. Move `.active`, then tear down. The page is
      already at 0 from the freeze, so no scroll reset is needed here.
- [x] 4.5 Write the abandon settle: transition both offsets back to rest, then
      on completion unfreeze the outgoing tab and restore the captured `scrollY`
      in the same synchronous block, with no paint between them. Comment that
      the forced layout is deliberately placed here, after the motion.
- [x] 4.6 Extend `endTabTransition()` to clear everything the drag adds: both
      freezes, the lift, the scrim, the window guard, the pending rAF handle,
      and the containment. Keep it idempotent and keep the safety timer.
- [x] 4.7 Keep `switchTabAnimated()` working for a commit that arrives without a
      drag — the shipped two-rAF path from rest. A tab change from any other
      control must still behave as it does today.

## 5. Rewire the gesture

- [x] 5.1 In `touchstart`: record the origin and refuse outright if any overlay
      is open or the touch began inside an overlay panel or backdrop. Do no
      other work — a tap and a vertical scroll must both stay free.
- [x] 5.2 In `touchmove`: resolve the axis at the lock distance, then hold it.
      Vertical releases the gesture for the rest of the touch. Horizontal calls
      `preventDefault()` from that move onward, runs the setup once, and hands
      every subsequent move to the tracker.
- [x] 5.3 Keep the listener non-passive from the start, so the first cancellable
      move can actually be cancelled.
- [x] 5.4 Track the last few move samples with timestamps so `touchend` can
      compute velocity from the end of the gesture rather than its average.
- [x] 5.5 In `touchend`: commit on distance ≥ ⅓ viewport **or** velocity above
      the flick floor, abandon otherwise, and no-op if the axis never locked.
      Do not latch — a drag past the threshold and back is an abandon.
- [x] 5.6 Bind `touchcancel` to resolve the drag. An incoming call mid-drag must
      not leave two tabs pinned and the grid frozen.
- [x] 5.7 Remove the first-load swipe tip and the `swipeThreshold` /
      `swipeAngleThreshold` constants it shared with the old handler. Remove
      `.swipe-indicator` from the markup and its CSS if nothing else uses it.
- [x] 5.8 Confirm the gate is unchanged: the drag is bound behind the same
      `isMobile` as before, and behind no media query.

## 6. Tests

- [x] 6.1 Extend `tests/test_tab_transition.py` — do not replace it. Every
      decision it currently pins still holds.
- [x] 6.2 Pin that the tracker reads no geometry: extend the existing
      forced-layout ban to the tracking and settle functions.
- [x] 6.3 Pin that the axis lock precedes `preventDefault()`, that the touch
      listener is non-passive, and that the lock distance is not the commit
      distance.
- [x] 6.4 Pin that `updateGridWindow()` has an explicit early return for a live
      drag.
- [x] 6.5 Pin that both tabs are frozen during a drag and that teardown clears
      each thing the setup sets — enumerated, so a new setup line without a
      matching teardown line fails.
- [x] 6.6 Pin that `touchcancel` is bound and that it routes to the same
      teardown.
- [x] 6.7 Pin that the overlay refusal happens at `touchstart`, not at
      `touchend`.
- [x] 6.8 Pin that the parallax ratio, the lift's scale and the settle's floor
      are tokens in `tokens.css` and are read back rather than restated.
- [x] 6.9 Pin that the sliding offset stays horizontal — no `translateY`, no Y
      custom property — while allowing the lift's `scale`.
- [x] 6.10 Pin that the pointer path still does not animate.
- [x] 6.11 Update the module docstring with what these can and cannot check for
      a drag, and with the numbers group 8 measures.

## 7. Docs

- [x] 7.1 Update the tab-transition section of `CLAUDE.md`: the horizontal-only
      rule now has a stated precondition rather than being absolute, the
      gesture is a drag, and the window guard is the reason the scale is
      admissible. Say why the guard is explicit.
- [x] 7.2 Note in `tools/README.md` how to drive a touch drag over CDP.
- [x] 7.3 Check `README.md` and `docs/` for anything describing the swipe as a
      threshold gesture or referencing the first-load tip. If nothing
      user-facing changed, say so explicitly rather than inventing edits.

## 8. Verify

- [x] 8.1 `make fmt`, then `make lint` and `make test`. Both must pass.
- [x] 8.2 Against a seeded library in a real browser over CDP: dispatch a drag
      path with known coordinates and assert the outgoing tab's offset
      corresponds to the finger at each one, and that a reversal reverses it.
      Correspondence, not merely change.
- [x] 8.3 Measure the frame cost of the tracked drag at library scale. Record
      median and worst frame, and the cost of the frame the setup lands on.
- [x] 8.4 Verify commit, abandon, resist, cancel and a second drag interrupting
      a settle each leave a correct resting state: right tab active, page
      scrollable, grid re-windowing, nothing pinned.
- [x] 8.5 Verify the abandon path returns the viewer to the scroll position they
      started at, from well down a long tab.
- [x] 8.6 Verify under `prefers-reduced-motion`: the follow still tracks, the
      settle is instant, the tab ends up right.
- [x] 8.7 Verify a vertical scroll and a tap on a card are both unaffected, and
      that a drag beginning inside the detail overlay dismisses it rather than
      moving the tabs.
- [x] 8.8 Record every measured number in `design.md` under the decision it
      settles, replacing the gate language with what was actually found.
- [x] 8.9 No `Dockerfile`, `config/` or entrypoint change is expected. If one
      turns out to be needed, run `make docker-smoke` before pushing.
      *Confirmed none was needed — the change is `web/`, `tests/` and `tools/`
      only, so the image is untouched and `make docker-smoke` does not apply.*
- [ ] 8.10 Validate on a real phone: the lift's scale against real artwork, the
      scrim's target, the flick floor, and whether the header's tab highlight
      should follow the drag or wait for the commit. These are the design's open
      questions and a thumb is the only instrument for them.
      **Outstanding — needs the `:dev` image and the user's hands. Do not
      archive before this.**
