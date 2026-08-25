## Context

Measured with `tools/browser.py` against a container seeded to 7,000 movies and
500 shows, at 390×844. Everything below is measured, not estimated.

**The render pipeline is one choke point.** `filterAndSortMedia()` filters by
search term, then by genre, sorts, and calls `displayMedia(sortedData, tab)`.
`displayMedia` is called from nowhere else. It empties the grid and builds one
element per item. So the whole change lands in one function, and every feature
that changes what is shown — search, sort, genre, tab — already funnels through
it.

**What `displayMedia` does per item, 7,000 times:**

| Per item | Cost at 7,000 |
| --- | --- |
| `createElement` + `innerHTML` + `appendChild` | 7,000 separate insertions |
| `style.transition = ...${index * 0.03}s` | last delay **209.97s** |
| `setTimeout(…, 10)` to flip opacity | 7,000 timers |
| `addEventListener('click', …)` | 7,000 closures |
| `imageObserver.observe(img)` | 7,000 observed targets |

**Measured consequences:** 63,248 DOM nodes; document 1,227,442px tall; 6 cards
on screen; ~3fps idle; scroll lock forces a 666ms relayout; 6,611 of 7,000 cards
still `opacity: 0` after 25 seconds.

**The grid's geometry is uniform.** `.media-grid` is
`repeat(auto-fill, minmax(var(--poster-width), 1fr))` with a fixed `gap`, and
every card is the same height (172.5×335.7px, 2 per row at 390px). Uniform rows
are what make a window's position computable without measuring each item.

**Caveat on the absolute numbers.** They come from headless Chromium; this
machine offers only SwiftShader, so software rasterisation cannot be separated
from what a phone's GPU would do. What is device-independent: the forced-layout
cost is CPU work scaling linearly with card count (0.7ms at 0 cards, 666ms at
7,000), the node count, and the 209.97s delay. The fix is justified by those,
not by the fps figure.

## Goals / Non-Goals

**Goals:**

- Rendered elements bounded independently of library size.
- Every item still reachable by scrolling, with no new navigation controls.
- Entrance delays derived from the window and capped.
- The change confined to `displayMedia()` and its helpers.

**Non-Goals:**

- Changing search, sort, genre filtering or the tabs. They filter the array;
  the window follows whatever they produce.
- Pagination, infinite-scroll affordances, or any "load more" control.
- Changing the snapshot schema, the fetchers, or anything server-side.
- Reworking the overlay system. The trays are not at fault and are not touched.
- Making the window size configurable. It is a constant with a measured
  justification, not a setting — see the frozen-compose rule.

## Decisions

### Recycle a window; do not merely append

Render a slice around the viewport and remove what falls far outside it,
maintaining the document's height with spacers.

*Alternative — append-only (render 100, append 100 more as the user nears the
bottom).* Much simpler: no spacers, no scroll maths, no removal. Rejected
because it does not bound anything — it defers. A viewer who scrolls to the end
of a 7,000 item library arrives back at 63,248 nodes and 3fps, having got there
gradually. "Correct unless you scroll far enough" is the conditional kind of
correctness this project keeps refusing: the failure returns silently, for the
users with the largest libraries, and looks like a different bug.

*Alternative — `content-visibility: auto` alone.* Measured: 2.5 → 7.5fps, lock
640 → 165ms. A real 3× for four lines of CSS and no JavaScript change. Rejected
as the whole answer because 7.5fps is still visibly broken, and the node count,
the timers and the 209.97s delay are all untouched. **Worth keeping as well** —
it is free, and it reduces the cost of whatever remains in the window.

### Hold the height with two spacers that span every column

The window's elements are the only real items in the grid, so the document would
otherwise collapse to the height of the window and the scrollbar would jump on
every extension. A spacer before and after, each sized to the rows it stands in
for, keeps `scrollHeight` equal to what the full selection would occupy.

They must declare `grid-column: 1 / -1`, or `auto-fill` places them as ordinary
cells and they consume grid positions — which shifts every following card into
the wrong column and makes the row maths wrong in a way that looks like an
off-by-one in the window rather than a layout bug.

Rows are uniform, so the arithmetic is exact rather than estimated:

```
perRow      = round(gridWidth / cardWidth)      # re-read, never assumed
rowHeight   = cardHeight + rowGap
rowsBefore  = floor(firstRendered / perRow)
spacerTop   = rowsBefore * rowHeight
```

`perRow` is read from the rendered grid rather than derived from a breakpoint,
because `auto-fill` decides it from the available width. A hardcoded column
count is the same class of mistake as the `280px` backdrop height that this
project already paid for once.

### Recompute the window on scroll, throttled to a frame

A `scroll` listener that recomputes on every event does layout work at the
scroll's own frequency. Coalesce with `requestAnimationFrame`, the same
mechanism the overlay scroll lock already uses.

The window is `[first - overscan, last + overscan]` where `first` and `last`
come from `scrollY`, `rowHeight` and the viewport height. Overscan of a few rows
means a fast flick does not outrun the render.

**Re-render only when the window actually moves.** Scrolling within the current
window must be free, or the fix reintroduces per-frame work by another route.

### Size the window from the measurements, and say why in the code

60fps held at 300 cards and 29.9fps at 800, so the ceiling is somewhere below
800. Six cards are on screen at 390px. A window of ~120 items sits an order of
magnitude below the measured ceiling and two orders above what is visible; it
leaves room for a desktop width with more columns without approaching 300.

The number goes in one named constant with the measured table beside it, so the
next person tuning it knows what the ceiling was and how it was found.

### Wire the grid once, not each card

- **Click** becomes one delegated listener on the grid, resolving the item via
  `closest('.media-item')` and its `dataset.id`. 7,000 closures become one, and
  a recycled card cannot leak a stale handler.
- **`imageObserver`** only ever sees cards that exist. Cards leaving the window
  are `unobserve`d, or the observer accumulates targets that have been removed —
  the leak that windowing is supposed to prevent, reintroduced.
- **Insertion** goes through a `DocumentFragment`, so a window arrives as one
  insertion rather than 120.

### Cap the entrance delay within the window

`index * 0.03s` becomes `min(indexWithinWindow * step, cap)`. The cap is the
decision that matters: an entrance animation softens an arrival the viewer is
watching, and a delay beyond a fraction of a second is not a softer arrival but
a missing item.

The 7,000 `setTimeout`s go with it — the opacity flip belongs to the same
fragment insertion, not to a timer per card.

## Risks / Trade-offs

**Scroll position moving under the viewer.** The failure mode of every windowed
list: the scrollbar jumps, or scrolling up lands somewhere else. → Spacer
heights are computed from uniform rows, so total height is invariant to which
window is rendered. Verified explicitly by holding a scroll position across a
window change and asserting the on-screen content has not moved.

**`perRow` changing on resize or orientation change.** Row maths computed for
two columns is wrong for five, and the page will look fine until it is resized.
→ Recompute `perRow` and `rowHeight` from the rendered grid on resize, and
re-render the window. Tested at 390px and 1280px, as the overlay work already
requires.

**`scrollPageTo` / scroll-to-top landing wrong.** The button scrolls to 0, which
is the one position where the window is trivially correct — but the overlay
scroll lock also restores a captured position, and that position must still mean
the same row after a window change. → Exercised in the browser with an overlay
opened and dismissed mid-library.

**The swipe indicator and the movies/TV swipe.** Item 5 is expected to become
possible here, not to be delivered here. This change must at minimum not break
the existing swipe. → Verified, not assumed.

**A test that cannot fail.** Asserting "the DOM is bounded" against a fixture of
50 items passes whatever the code does — the exact trap `docs/handover.md`
records for this item. → The bound is asserted against a seeded library large
enough to fail the old code, in a real browser.

## Open Questions — both resolved during implementation

- **Should the window also apply below some library size?** **Resolved: always.**
  One code path. A size-conditional path is only ever exercised by the users who
  have the large library, which is the population it would be hiding bugs from.

- **Does `content-visibility` stay once windowing lands?** **Resolved: no.**
  Measured at the final window size of 120 cards, 390×844: frame rate identical
  with and without (both 16.7ms — already at the display's cap, so there is
  nothing left for it to win). The scroll lock's forced relayout improves
  10.8ms → 4.7ms, which is real but is an operation already comfortably inside a
  16.7ms frame.

  The deciding argument is not the margin, it is `contain-intrinsic-size`: it
  would hardcode the card's width and height in CSS while `measureGrid()` reads
  those same dimensions from the rendered DOM. Two sources for one number, one
  of them a constant that no longer changes when the card does. That is the
  drift this project keeps paying for, bought here for a saving on an operation
  that already fits in a frame.

## Corrections made during implementation

Recorded because both were wrong in a way that cost time and would cost it
again.

- **`overflow-anchor: none` was added to fix an oscillation it did not cause.**
  The grid appeared to converge on a scroll position over several hundred
  milliseconds, which looks exactly like scroll anchoring fighting a windowed
  list. It was `scroll-behavior: smooth`, set on the document, still in flight —
  the test was reading a position the user never occupied. Measured afterwards
  with anchoring on and off: drift was zero either way. The property is kept as
  a guard against a real documented interaction, with a comment saying plainly
  that it has not been observed to do anything here.

- **Rows must be measured from the grid's CONTENT box.** `.media-grid` has
  `padding: 20px 0`, so measuring from the border box puts every row boundary a
  fifth of a row out — not enough to look broken, enough to select the wrong row
  near a threshold.
