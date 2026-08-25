## 1. Measurement gate — run BEFORE writing any transition CSS

This group decides whether the change is the slide or the fallback cross-fade.
Do not start group 3 until 1.5 has an answer.

**Result: GO for the slide.** Numbers and consequences recorded in `design.md`.
The transform costs nothing at 1.2M px; the `height: 100vh; overflow: hidden`
bound is dropped as measured-worthless; a forced layout during the freeze is the
one real hazard and is avoidable.

- [x] 1.1 Build the dev image and stand up a container seeded to library scale,
      following `tools/README.md`: `python tools/seed_library.py --out /tmp/seed
      --posters 60`, run the container, then `docker cp` the snapshots in —
      the entrypoint fetches on every start and a fetch that cannot reach a
      media server DELETES the snapshots, so they must be copied after boot.
      Seed thousands of items; a few-hundred-item fixture cannot fail these
      numbers and has already let this class of bug through once.
      **Note:** the README's own recipe seeds *into* the bind-mounted directory,
      so the entrypoint deletes the pristine copy along with the container's.
      Seed to a directory outside the mount and `docker cp` from there.
- [x] 1.2 Record a `--label before` baseline with `tools/grid_metrics.py` at
      390px and 1280px, so the transition's cost has something to be compared
      against. **1,297 nodes / 59.9fps / 1,227,442px document at 390px.**
- [x] 1.3 Drive a real Chromium through `tools/browser.py` and, by hand in the
      page, apply the frozen state to `#movies-content` — `position: fixed`
      offset by `-scrollY`, plus `height: 100vh; overflow: hidden` — then
      animate a `translateX` across it. Use `Browser.viewport()`, never raw
      `Emulation.setDeviceMetricsOverride`: `mobile: true` silently yields a
      980px layout viewport on a page with no `<meta name="viewport">`, so a run
      labelled 390px would be measuring desktop.
- [x] 1.4 Repeat 1.3 **without** the `height: 100vh; overflow: hidden` bound, so
      the measurement says what the bound is worth rather than assuming it. The
      unbounded case puts a transform on a box over a million pixels tall.
      **Result: identical on frame rate and on scrollable overflow. Bound
      dropped.**
- [x] 1.5 **Go / no-go.** Record both frame rates in `design.md` under a
      "Measured" heading. If the bounded transform holds a smooth frame rate,
      proceed with the slide. If it does not, stop and revise the proposal and
      the direction-of-travel scenarios in
      `specs/media-browsing/spec.md` to the cross-fade fallback (approach C)
      before writing any code — do not ship the specs unmet.
      **GO.** 59.9fps, zero dropped frames, bounded and unbounded, both widths.

## 2. Make a tab renderable while it is inactive

- [x] 2.1 Give `filterAndSortMedia()` a `type` parameter defaulting to the
      active tab, so all five existing call sites keep today's behavior
      verbatim and only the transition passes something else.
- [x] 2.2 Verify by hand that a tab rendered while inactive resolves its own
      data with the current search term, genre filter and sort order, and that
      `displayMedia()` clears that tab's `.loading` spinner — the inactive tab
      has never been rendered before, so its spinner is visible from first paint
      and this is the first code path that retires it.
      **Verified in the browser.** Before: `#tvshows-content` had 0 cards and a
      live spinner (`display: flex`), confirming the premise. After rendering it
      while `#movies-content` was still active: 120 cards of its own data,
      spinner `none`, movies untouched and still active.

## 3. Reorder `switchTab()` around the transition

- [x] 3.1 Split the non-visual half of `switchTab()` — genre reconcile,
      `updateGenreUI()`, closing the Actions tray, moving `.tab.active` — from
      the visual swap, so both the instant path and the animated path drive the
      same state changes and cannot diverge.
- [x] 3.2 Keep the pointer path byte-for-byte in behavior: instant swap, then
      `window.GlimpseOverlays.scrollPageTo(0)`. Nothing about a tab click
      changes.
- [x] 3.3 Implement the animated path in the freeze order from `design.md`:
      freeze the outgoing tab (`position: fixed`, offset `-scrollY` — no
      `height`/`overflow` bound, measured worthless in 1.4), `scrollPageTo(0)`,
      render the incoming tab offset by
      `translateX(100%)`, animate both, then tear down. Route the scroll through
      `scrollPageTo()` — an overlay may hold the scroll lock — and pass
      `behavior: 'instant'` where a scroll is issued, because
      `scroll-behavior: smooth` is set on the document and would otherwise
      animate for about a second under the transition.
- [x] 3.4 Read **no** geometry between freezing the outgoing tab and starting
      the transition — no `getBoundingClientRect`, no `offsetHeight`, no
      `getComputedStyle` of a layout property. Measured in 1.3: setting the
      frozen styles costs 0.2–0.4ms, reading the box back afterwards costs
      **77.7ms** and lands on the animation's first frame. Say so in a comment
      at the freeze, because the symptom is "the animation is janky" and the
      transform is what gets blamed.
- [x] 3.5 Write the teardown as one idempotent function, invoked both by the
      transition ending and by a new transition starting. It must leave neither
      tab holding a transform, a fixed position, an imposed offset or an
      overflow constraint.
- [x] 3.6 Guard against a swipe committing mid-transition: resolve to exactly
      one active tab showing its own contents, with nothing left displaced.

## 4. CSS

- [x] 4.1 Add the transition's duration and easing to `web/assets/tokens.css`
      and read them from there — never restate a number at the use site. Match
      the overlay trays' 280ms unless the browser says otherwise.
- [x] 4.2 Translate on the horizontal axis only. `firstVisibleRow()` derives the
      window's first row from `grid.getBoundingClientRect().top`, so a
      `translateY` or a scale corrupts the row arithmetic mid-transition and
      presents as a windowing bug. Say so in a comment at the rule.
- [x] 4.3 Resolve `.content`'s existing `opacity` / `translateY` / `transition`
      declarations, which have never run because `display: none` →
      `display: block` does not transition. Either express the working
      transition there or delete them; do not leave a rule that appears to
      animate the tabs and does not.
- [x] 4.4 Contain horizontal overflow for the transition's duration only, so the
      incoming tab at `translateX(100%)` cannot open a horizontal scrollbar, and
      the containment cannot outlive the animation. Measured in 1.4 and real:
      `scrollWidth` reaches 750px against a 390px `clientWidth`.
- [x] 4.5 Confirm the transition inherits the app-wide
      `prefers-reduced-motion` block in `tokens.css` — it collapses duration to
      0.01ms rather than removing the transition, so any `transitionend` the
      teardown relies on still fires.

## 5. Gate it with the gesture

- [x] 5.1 Enable the animated path inside the same `isMobile` condition that
      binds the swipe listeners. No separate media query and no second
      breakpoint: one condition cannot drift from itself, and this project has
      already shipped a pair of related rules that reached 992px and 768px
      independently.
- [x] 5.2 Pass the swipe's direction through to the transition so the outgoing
      tab leaves toward the finger, and confirm both directions.

## 6. Verify in a real browser

- [x] 6.1 At 390px, with the seeded library: swipe both directions and confirm
      one continuous movement — no scroll jump before or after — landing at the
      top of the incoming tab.
- [x] 6.2 Confirm the **first** switch to a tab shows no loading spinner at any
      point during the transition. This is the case that only ever exists once
      per page load, so it must be tested on a fresh load.
- [x] 6.3 Swipe again mid-transition and confirm exactly one tab ends active
      with correct contents and nothing left displaced.
- [x] 6.4 Confirm a tab switch during an open overlay still lands correctly and
      the overlay restores the new scroll position on close.
- [x] 6.5 At 1280px, confirm tab clicks are still an instant cut and that
      scrolling, windowing and the overlays are unregressed.
- [x] 6.6 Re-run `tools/grid_metrics.py --label after` at both widths and
      compare against the 1.2 baseline.
- [x] 6.7 Do **not** verify any of this with `chromium --headless
      --virtual-time-budget --dump-dom`. `requestAnimationFrame` never fires
      under it, so it cannot observe a transition at all, and it has already let
      five bugs reach the user while reporting everything fine. Use
      `tools/browser.py`, which is committed — do not rebuild it.

## 7. Tests and docs

- [x] 7.1 Add `tests/test_tab_transition.py` pinning the source decisions this
      change makes, in the style of `tests/test_grid_windowing.py`: the
      transition is gated on the same condition as the gesture, the translate is
      horizontal-only, `.content` carries no dead transition declaration, and
      the teardown clears every property the freeze sets. `make test` has no
      browser and cannot assert the animation itself — the browser half of the
      verification is group 6, and neither half is worth having alone.
- [x] 7.2 Demonstrate each new assertion failing against the specific bug it
      describes before committing it. Every regression test in this repo was
      shown to fail first; a passing markup test is not a passing feature.
- [x] 7.3 Record the measured numbers from group 1 in the source, next to the
      decision they justify, the way the windowing table is recorded in
      `web/index.html`.
- [x] 7.4 Check whether `README.md`, `docs/` or `CLAUDE.md` are made stale by
      this change and fix them in the same commit. If nothing user-facing
      changed, say so explicitly rather than inventing edits.
- [x] 7.5 Run `make lint` and `make test`. No `Dockerfile`, `config/` or
      entrypoint change is involved, so `make docker-smoke` is not required —
      confirm that is still true before skipping it.

## 8. Decide the open questions

- [x] 8.1 Ask the user whether the `.swipe-indicator` toast stays now that the
      motion states the direction of travel. Ship it unchanged unless they say
      otherwise.
      **Asked and decided: drop the post-swipe toast, keep the first-load tip.**
      The slide confirms the gesture and states its direction, which the toast
      never did; the tip teaches a gesture that is otherwise undiscoverable and
      has no replacement. Verified in the browser: tip still fires, no
      "Switched to…" text after a swipe, tab still switches.
- [x] 8.2 Confirm the transition duration against the real thing rather than the
      spec sheet, and note whether it matches the overlay trays.
