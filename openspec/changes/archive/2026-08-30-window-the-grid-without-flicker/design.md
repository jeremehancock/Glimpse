## Context

The grid renders a window near the viewport rather than the whole library. Two
defects sit in how that window is anchored and how its geometry is obtained. They
present as opposites — one tab flickers, the other does not — and the second is
what hides the first.

**Measured shape of the flicker.** At two columns the window is
`ceil(120 / 2) = 60` rows. On a Pixel a row is roughly 362px, so the window
holds about 21,700px of runway. `desiredFirstIndex()` is
`(firstVisibleRow - GRID_OVERSCAN_ROWS) * perRow`, which changes every time the
viewer crosses one row — about every 362px. `updateGridWindow()` compares that
against `view.first` and, on any difference, calls `renderWindow()`, whose final
act is `grid.replaceChildren(...)` over freshly built cards. Every card in the
window is a new element carrying `<img data-src>` with no `src`, `opacity: 0`,
and a spinner placeholder; the `IntersectionObserver` then re-lazy-loads each
one. So roughly 1.7% of the window's contents changes and 100% of what the
viewer is looking at is destroyed.

The anchor is also asymmetric: four rows above the viewer, fifty-six below. That
is why scrolling up is the worst case, and why the user reported it over posters
that had already loaded.

**Measured shape of the geometry defect.** `.content { display: none }` hides the
inactive tab. `beginTabTransition()` calls
`filterAndSortMedia(searchTerm, contentName, false)` *before* `commitTabState()`
adds `.active` — deliberately, to satisfy the existing requirement that no part
of an incoming tab is visible before it has been rendered. `displayMedia()` then
calls `measureGrid()` against that hidden grid, where
`card.getBoundingClientRect().height` is `0`, so `view.rowPitch = 0`. The retry
guarded by `if (view.rowPitch <= 0)` re-measures while still hidden and gets `0`
again.

`updateGridWindow()` bails on `view.rowPitch <= 0`, so windowing is off for that
tab permanently. `sizeSpacer()` then computes `rows * 0 - rowGap` = `-15px`;
negative heights are invalid CSS, the assignment is silently dropped, and the
bottom spacer stays at zero. The tab renders one window and the document ends.

At phone widths `.header-content .tabs { display: none }`
(`@media (max-width: 768px)`), so the swipe is the only entrance to the other
tab — and it is the entrance that breaks it. Confirmed by the reporter: rotating
the device fires `resize`, which re-measures against a now-visible grid, restores
the full scroll extent, and makes that tab begin flickering like the other one.

The two interact: the flicker is what correct windowing currently looks like, so
fixing either defect alone gives a misleading reading of the other.

## Goals / Non-Goals

**Goals:**

- Scrolling within the window rebuilds nothing.
- A re-anchor that does happen is invisible: already-loaded artwork is not
  returned to a placeholder.
- Upward scrolling carries runway comparable to downward.
- Geometry is never recorded from a grid without layout, and an unmeasured grid
  is distinguishable from one that needs no window.
- The whole library stays reachable on the tab reached by the swipe, with no
  rotation required.

**Non-Goals:**

- Changing the window size. `GRID_WINDOW_ITEMS = 120` is measured and holds; the
  defect is the re-anchor policy, not the bound.
- Recycling DOM nodes across renders. It would make the question moot, but it is
  a larger change and the two fixes below are expected to remove the symptom
  without it. Left as the fallback if measurement says otherwise.
- Rendering the incoming tab later than it is rendered now. That ordering
  satisfies an existing requirement and is not in question — only the
  measurement taken alongside it is.
- Touching the artwork caching strategy, the service worker, or any nginx header.
  Posters already come from cache; nothing here is a network problem.
- Restoring the tab controls at phone widths. Their absence explains why the
  swipe path matters, but the swipe is the intended entrance.

## Decisions

### Re-anchor on edge approach, and centre the window

Keep the window where it is while the viewer is comfortably inside it; move it
only when they come within the overscan of an edge, and when moving it, place it
so the viewer sits near its middle.

Centring is what gives upward scrolling its runway, and it makes the re-anchor
distance roughly half the window in either direction rather than four rows up
and fifty-six down. Combined, a traversal of the window costs about two rebuilds
instead of about sixty.

*Alternative — a fixed hysteresis of N rows.* Simpler, but N is a second number
that has to stay in a relationship with the window size and the overscan, and
this repo has already shipped pairs of numbers that were meant to be related and
drifted. Deriving the trigger from the window's own edges keeps one source.

*Alternative — recycle nodes instead of replacing them.* Strictly better and
strictly larger. Held as the fallback; see Non-Goals.

### Present already-loaded artwork as loaded

Track the poster paths whose images have loaded. When `buildCard()` builds a card
whose poster is in that set, emit the `src` directly with the loaded class and no
placeholder, so the browser paints it from cache without an observer round trip,
a load event, or a fade.

This makes a re-anchor invisible rather than merely rarer, which matters because
re-anchors do not go away — they become uncommon. It also removes the flicker
from any future path that rebuilds a card.

The set is per-session and bounded by the number of distinct posters the viewer
has actually scrolled past, not by library size. It holds paths, not images; the
browser's own cache holds the bytes.

*Alternative — keep the placeholder but skip the fade.* Still shows a placeholder
frame between insertion and decode. Halves the symptom rather than removing it.

### Refuse to record geometry from a grid without layout

`measureGrid()` should determine whether it is looking at a laid-out grid and, if
not, leave the view's geometry untouched and mark it unmeasured. A grid with no
layout reports zero height for its cards; that is the signal, and it is available
without asking the tab whether it is currently displayed.

Deciding it from the measurement rather than from tab state is deliberate. A
check like "is this tab active" is a second condition describing the same fact,
and it has to be kept in step with every path that renders a hidden tab —
`beginTabTransition()`, `warmInactiveTab()`, and whatever comes next. A
measurement that can tell it failed cannot drift from itself. It is the same
reasoning as the overlay system keying on the DOM rather than on a registry.

### Separate "unmeasured" from "no window needed"

`rowPitch = 0` currently means both. Give the view an explicit unmeasured state
so `updateGridWindow()`'s early return is a deliberate refusal rather than an
accident of arithmetic, and so a grid that has never been measurable cannot look
like a healthy one.

This is the part that turns the defect from silent into loud. The present failure
is a tab that renders, scrolls, looks correct, and quietly omits most of the
library — the same shape as a misconfigured install that looks like a working
one, which this project refuses everywhere else.

### Measure when the tab becomes visible

A tab rendered while hidden needs its geometry taken once it is laid out. The
natural moment is when it becomes the active tab — after `commitTabState()` — and
before its window is next moved.

The existing `resize` handler already does exactly this repair by accident, which
is what the reporter's rotation demonstrated. The fix is to reach the same state
without requiring a resize, not to add a new mechanism.

*Alternative — force layout on the hidden grid.* Would need it temporarily
visible or off-screen-but-rendered, which either flashes content or reintroduces
the whole-library layout cost this design is trying to avoid.

## Risks / Trade-offs

**A centred window changes which items are rendered at a given scroll position,
and the tab transition depends on window position.** `renderSignature()` treats
the window position as part of what is rendered, and `filterAndSortMedia()`'s
skip path calls `renderWindow(view, 0, false)` on the assumption that a tab about
to be shown from its top needs its window at the top. → Re-check that path against
the new anchoring rule; a tab shown at scroll 0 must still have its window there.
The existing spec requirement covering this stays as it is.

**The loaded-poster set could grow without bound in a long session.** → It holds
short strings keyed by item, bounded by distinct posters actually viewed, not by
library size. If measurement shows it matters, it can be capped; it should be
measured before it is optimised.

**Marking a grid unmeasured makes the refusal louder, and a path that renders
before measuring will now render nothing rather than something wrong.** → That is
the intent, but it means every render path must reach a measurement. The tab
paths, the warm path, the search/sort path and the resize path all need checking,
not just the swipe.

**`make test` cannot verify any of this.** A zero-height measurement needs a
browser and the flicker needs a library large enough to scroll a window through.
→ Source decisions pinned in `tests/test_grid_windowing.py`; behaviour measured
with `tools/grid_metrics.py` against a seeded library. Both halves, per the split
that test file already documents.

**The test that pins the current re-anchor guard encodes the defect.**
`test_scrolling_inside_the_window_does_nothing` asserts
`if (first === view.first) return;` and is named for a guarantee the code has
never provided on a phone — the guard means "the anchor has not moved", not "the
viewer is inside the window". → It must be rewritten to pin the new policy, not
relaxed to let the change through. A test derived from a spec inherits the spec's
blind spot, and this one did.

**Verifying a fix for a flicker is a frame-level problem.** A screenshot of a
resting grid shows nothing, and every screenshot ever taken of this grid looked
fine. → Verify by driving a real scroll over CDP and sampling across frames,
never by a single point. Confirm both directions: the reported symptom was
upward, and the downward case is the one that looks fixed first.

## Migration Plan

None. No persisted state, no data format, no configuration. The change is
confined to rendering in `web/index.html`; a rollback is a revert.

Worth noting for the release: on a phone the swiped-to tab currently shows only
its first window, so shipping this makes items visible that were previously
unreachable. That is the fix working, not a data change.

## Open Questions

- Does the reporter's TV Shows tab in fact stop after ~120 items? The mechanism
  says it must and the rotation result corroborates it, but it was not directly
  confirmed. It changes nothing about the fix; it changes how the release note
  describes what users get back.
- Should `GRID_OVERSCAN_ROWS` still be the edge trigger once the window is
  centred, or should the trigger be a fraction of the window? Decide against
  measurement rather than in advance — the goal is that a normal scroll rebuilds
  about twice per window traversal.
- Do the two unthrottled, non-passive `scroll` listeners at `index.html:4470` and
  `index.html:4489` contribute enough on Android to be worth folding into the
  existing rAF-coalesced scheduler? They are a separate defect from this one and
  should not ride along silently if they are not measured to matter.
