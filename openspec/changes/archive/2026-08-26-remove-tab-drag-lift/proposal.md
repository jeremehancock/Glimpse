## Why

Swiping between tabs currently drops the whole grid downward the instant the
gesture is claimed, and lifts it back on release. The horizontal movement reads
well; the vertical one reads as the page glitching, and it is the first thing a
viewer notices because it happens before anything has slid anywhere.

It is the lift's scale. The moving tabs are scaled to 0.94 about the centre of
the viewport, so everything above that centre moves toward it — at a 780px
viewport the top row of cards falls about 23px, immediately, with no easing.
That was intended as depth ("a card the viewer is pushing aside") and it is
being received as vertical motion in a horizontal gesture.

## What Changes

- The tab drag's lift is removed entirely. A dragged tab is no longer scaled and
  the page behind it is no longer dimmed. The gesture becomes exactly what it
  reads as: two full-width panels sliding horizontally, 1:1 with the thumb.
- `--tab-drag-lift` and `--tab-drag-scrim` are removed from the token set, along
  with the `.tab-dragging::after` scrim and the `--tab-origin-y` /
  `transform-origin` machinery that existed only to anchor that scale.
- The scrim goes with the scale rather than surviving it. Without the scale the
  two tabs are each a full viewport wide and sit edge to edge, so no gap between
  them ever opens and a dim behind them could never render. Keeping it would
  leave live code that cannot succeed, which this project has already been bitten
  by twice.
- **A pinned tab keeps its own horizontal box.** Found by the browser pass, not
  predicted: the freeze pinned each tab with `left: 0; right: 0`, and a fixed
  element does not inherit `.container`'s padding — so claiming a gesture widened
  the grid by both paddings (+20px, ~10px per card at two columns) and released
  it back. That predates this change and had never been seen, because the lift's
  scale shrank the over-wide tab back to within 2px of its in-flow width. One
  accident cancelled another. Removing the lift uncovers it, and a grid that
  changes size when a thumb lands is the same complaint as one that drops, so the
  box is now written inline from the rect the freeze already reads.
- Everything else about the gesture is unchanged: the axis lock, the 1:1 follow,
  the commit threshold and flick test, the resisted end, the settle timing, the
  freeze of both tabs, and the abandon path.
- The refusal to re-window the grid during a drag **stays**, and its stated
  reason changes. It is currently justified by the scale moving every card's
  measured top; with the scale gone it stands on its own — a safety that rests on
  "a pinned tab receives no scroll events" is a safety that disappears the next
  time the mechanism changes, which the spec already says.

Not a breaking change. Nothing here touches the frozen `docker-compose.yml`
surface: no environment variable, no port, no volume, no image name. An existing
user's compose file is unaffected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `visual-design`: the requirement "A tab being dragged is lifted off the page"
  is removed. A dragged tab has no raised presentation — no scale, no scrim — and
  the reduced-motion scenario attached to that lift goes with it.
- `media-browsing`: the requirement "The grid's rendered window does not move
  while the tabs do" is kept but re-justified — it no longer rests on a scale
  that no longer exists. The requirement that the sliding transform stays
  horizontal is strengthened: with the lift gone there is no exception to it at
  all.

## Impact

- `web/assets/tokens.css` — the two lift tokens and the block of commentary that
  explains them.
- `web/index.html` — the `.content.tab-leaving` / `.tab-entering` transform and
  `transform-origin`, the `.tab-dragging::after` scrim rule, the `tab-dragging`
  class, `TAB_LIFT`, `pinTab()`'s origin write, and the `--tab-lift` set/clear
  sites in the drag, the resisted path, the settle and the teardown.
- `tests/test_tab_transition.py` — the tests that assert the lift exists
  (`test_the_lift_is_a_scale_and_a_scrim_only`, the token-ownership assertion for
  `--tab-drag-lift` / `--tab-drag-scrim`) invert: they must now assert the lift
  is gone. The two conditional tests that return early when no `scale(` is
  present (`test_the_lift_is_paired_with_a_windowing_refusal`,
  `test_a_scaled_tab_anchors_its_origin_to_the_viewport`) become unconditional in
  the other direction — no scale may appear on those rules.
- `CLAUDE.md` — the paragraph "The lift is a SCALE AND A SCRIM" and the
  transform-origin lesson under it describe behaviour that will no longer exist.
- No Python, no `Dockerfile`, no `config/`, so no `make docker-smoke` gate.
- Verification needs a real browser: nothing in `make test` can see a 23px
  vertical displacement.
