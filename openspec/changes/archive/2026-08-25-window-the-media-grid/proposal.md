## Why

At a real library size the grid does not work. Measured against a seeded 7,000
movie library in a real browser at 390×844:

- The page renders **63,248 DOM nodes** in a document **1,227,442px tall**, of
  which **6 cards are on screen**.
- It sits at **~3fps while idle**, with nothing animating and no overlay open.
- **6,611 of 7,000 cards are still `opacity: 0`** after 25 seconds. The last
  card's `transition-delay` is **209.97 seconds**.

This is punch-list item 2 ("mobile trays are choppy"), and the tray was the
symptom rather than the problem. A tray's 280ms open animation gets roughly one
frame, so it does not slide — it jumps. Nothing about the transition is wrong.

Frame rate against card count, same page, cards removed progressively:

| Cards | DOM nodes | Idle | Scroll-lock relayout |
| --- | --- | --- | --- |
| 7000 | 63,248 | 3.0fps | 666ms |
| 2000 | 18,248 | 10.9fps | 178ms |
| 800 | 7,448 | 29.9fps | 71ms |
| 300 | 2,948 | 59.9fps | 28ms |
| 100 | 1,136 | 59.9fps | 7.5ms |
| 0 | 236 | 59.9fps | 0.7ms |

60fps holds to roughly 300 cards and collapses past 2,000. A CPU profile over
two idle seconds is **96.8% `(program)`** — browser style, layout and paint, not
application JavaScript. Setting `display: none` on the grid restores 60fps
instantly with all 63,248 nodes still in the document, so the cost is the grid
being laid out, not the nodes existing.

## What Changes

- **The grid renders a window near the viewport instead of the whole library.**
  `displayMedia()` keeps its signature and its place in the pipeline — it is the
  single choke point, called only by `filterAndSortMedia()` — but it renders a
  slice and extends it as the user scrolls. The full filtered array stays in
  memory; only the DOM is bounded.
- **The staggered fade-in is bounded.** `index * 0.03s` is a per-item
  `transition-delay` computed from the item's position in the whole library, so
  it passes three seconds at item 100 and 3.5 minutes at item 7,000. It becomes
  a delay computed within the rendered window, capped so no card waits longer
  than the animation itself.
- **Per-card wiring becomes per-grid wiring.** Today every card gets its own
  `click` listener and its own `IntersectionObserver.observe()` call — 7,000 of
  each. The click becomes one delegated listener on the grid; the observer is
  only asked about cards that exist.
- **Cards are inserted in one batch, not appended one at a time.**

**No change to what the user can reach.** Every item remains browsable by
scrolling, and search, sort, genre filter and the movies/TV tabs keep operating
on the complete data set — they filter the array, and the window follows the
result. This is not pagination and adds no page controls.

The frozen `docker-compose.yml` surface is **untouched**: no environment
variable, port, volume or image name is involved, and nothing here is
configurable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-browsing`: adds requirements that the grid's DOM cost be bounded
  independently of library size, that every item remain reachable by scrolling,
  and that an item's entrance animation not be scheduled from its position in
  the library.

## Impact

| Area | Change |
| --- | --- |
| `web/index.html` — `displayMedia()` | Renders and extends a window; batch insert; delegated click |
| `web/index.html` — the stagger | Delay computed within the window and capped |
| `web/index.html` — `imageObserver` | Observes only rendered cards; unobserves on recycle |
| `tests/` | New tests pinning the bound and the reachability of the last item |

Expected to also resolve **punch-list item 5** (animating the movies/TV swipe),
which was blocked on the same cause: a transform on a container holding 63,248
nodes cannot be smooth, and the handover already predicted the two are one
problem.

**Risk worth stating up front:** scroll position and `scrollHeight` become
things the grid manages rather than consequences of the content. Getting that
wrong produces a scrollbar that jumps or a scroll-to-top that lands in the wrong
place — both visible, neither caught by a unit test. The design addresses how
the window is sized and extended, and the verification is in a real browser at
both widths.
