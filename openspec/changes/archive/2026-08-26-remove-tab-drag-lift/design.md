## Context

The tab drag ships and works: both tabs freeze out of the scroller, follow the
thumb 1:1 a full viewport apart, and settle over a duration scaled to the
distance left. On top of that, claiming the gesture applies a "lift" — the two
panels scale to `--tab-drag-lift` (0.94) and a scrim (`--tab-drag-scrim`) dims
the root behind them.

The scale is anchored, by `pinTab()`, to the centre of the viewport expressed in
the panel's own coordinates. That anchoring is itself a fix: the default origin
is the element's own centre, and a tab holding 7,000 items is over 1.2 million
pixels tall, so scaling about it threw the grid tens of thousands of pixels
downward. Anchoring to the viewport centre bounds the displacement — it does not
eliminate it. A 0.94 scale about the viewport's midpoint moves the top edge of
the viewport down by `0.03 × viewportHeight`: about 23px on a 780px phone. That
lands instantly at the axis lock, before any horizontal travel, and reverses on
release.

Which is what the viewer reported: the grid drops when you swipe.

Constraints this has to respect, all of them already load-bearing in this file:

- The freeze reads no geometry after its first write. `beginTabTransition()`
  takes exactly one `getBoundingClientRect()`, above every write, and a read
  after a write measured at 77.7ms on the gesture's opening frame.
- `updateGridWindow()` refuses to run while a gesture is live, and that refusal
  is stated rather than implied.
- The tabs sit a full viewport apart and never overlap; they share a `z-index`,
  which is only safe because of that.
- Tokens live in `tokens.css` and are read from there, never restated.
- Nothing under `web/` is built. Every change is to authored files nginx serves
  as-is.

## Goals / Non-Goals

**Goals:**

- No vertical movement of grid content at any point in the gesture, and no size
  change.
- The lift removed as a unit — scale, scrim, transform-origin machinery, tokens,
  and the branch that switches it on — leaving no rule or property that renders
  nothing.
- The horizontal drag identical in every other respect: axis lock at 8px, 1:1
  follow, one-viewport separation, third-of-viewport-or-flick commit, resisted
  ends, distance-scaled settle, abandon and cancel paths.
- The windowing refusal kept, and re-grounded so it does not read as orphaned
  once the scale it cites is gone.

**Non-Goals:**

- Any substitute for the lift. No gap between the panels, no seam, no shadow, no
  radius, no dim. The user chose the plain slide.
- Any change to the non-drag transition (tapping a tab button), beyond it losing
  a `lifted: false` argument it never used.
- Any change to timing tokens, the commit test, or the settle curve.
- Any change to overlays, chrome layering, or the grid windowing algorithm.

## Decisions

### 1. Remove the lift whole, not just the scale

What the scrim dimmed was the gap the scale opened — 23px of page down each side
of each panel, which is what made them read as lifted. Remove the scale and what
remains between the two tabs is the page's own padding gutter: the same strip of
background the page shows at its edges at rest. Dimming that does not read as
depth. It reads as a tinted stripe tracking the thumb, which is exactly how the
drop shadow failed before it, and it would be the only dimmed thing on a screen
that is otherwise entirely covered by the two panels.

So the scrim goes with the scale. `--tab-drag-scrim`, the `::after` rule, and the
`tab-dragging` class all go — the class has no other consumer; a grep finds the
rule, two `add`s and the `remove` in teardown.

So `--tab-drag-scrim`, the `::after` rule, and the `tab-dragging` class all go.
The class has no other consumer — a grep for it finds the rule, one `add`, one
`add`, and the `remove` in teardown.

*Alternative considered:* keep the scrim by parking the incoming tab at
`width + gap` so a fixed 24px seam tracks the thumb. Rejected by the user, and
independently it would resurrect a decision already reversed once: a gap tracking
the thumb is what the removed shadow rendered as, and it read as noise.

### 2. `transform-origin` goes with the scale, and so does `pinTab()`'s second job

With `transform: translateX(...)` alone, `transform-origin` is inert — a
translation is origin-independent. Leaving `transform-origin: 50%
var(--tab-origin-y, 50%)` behind would be a declaration that appears to set
something and sets nothing, which `visual-design` already forbids by name.

`pinTab(panel, viewportTop, middle)` therefore loses its `middle` parameter and
its `--tab-origin-y` write. `beginTabTransition()` and `beginResistedDrag()` each
stop computing `viewportMiddle`. What it gains instead is decision 6 below.

The long comment above `pinTab()` explaining the +36,791px displacement does not
survive as documentation of live behaviour. Its lesson — that a transform on a
panel this tall is a *visible* hazard and not only an arithmetic one — is worth
keeping, so it moves into the note explaining why these panels are translated and
nothing else. That is the same lesson, stated as a rule instead of as a war story
about code that no longer exists.

### 3. The windowing refusal stays and is re-grounded

`updateGridWindow()`'s refusal is currently justified in both the code and the
spec by the scale moving every card's `getBoundingClientRect().top`. Remove the
scale and that justification evaporates, which is exactly the setup for someone
deleting the guard as dead weight.

It is not dead. A pinned tab is at a captured offset, not at the viewer's scroll
position, so a window computed mid-gesture is computed against a position the
viewer never occupied. The requirement is restated on that basis in the
`media-browsing` delta, the code comment is rewritten to match, and
`test_the_lift_is_paired_with_a_windowing_refusal` — which today returns early
when no `scale(` is found, and would therefore go quietly green and stop testing
anything — is rewritten to assert the refusal unconditionally.

That early-return is the single most likely way this change breaks something
later, which is why it gets its own task.

### 4. The tests invert rather than being deleted

Three tests in `tests/test_tab_transition.py` assert the lift exists or guard how
it is built:

| Test | Becomes |
| --- | --- |
| `test_the_lift_is_a_scale_and_a_scrim_only` | asserts no scale, no scrim, no `tab-dragging`, no lift tokens — the lift is gone and no substitute (shadow, radius, gap) took its place |
| `test_a_scaled_tab_anchors_its_origin_to_the_viewport` | asserts the tab transform is a translate only, so there is no origin to get wrong |
| `test_the_lift_is_paired_with_a_windowing_refusal` | asserts the refusal exists, with no `scale(` precondition |

The token-ownership test loses `--tab-drag-lift` and `--tab-drag-scrim` from its
list and keeps `--dur-tab-settle-min`, which is unaffected.

Deleting them instead would leave nothing standing between the next contributor
and a re-added scale. An inverted test is the artifact that carries this
decision forward; the spec is the argument, the test is the enforcement.

### 5. `make test` cannot see this bug, so the verification is a browser drag

A 23px vertical displacement is invisible to pytest, which reads source text. The
implementation is verified by driving a real drag over CDP and asserting on a
card's rect across the gesture:

- `rect.top` constant (within a pixel) from before the axis lock through the full
  drag — this is the bug, stated as a measurement.
- `rect.width` constant — no scale.
- `rect.left` corresponding to the finger at each sampled coordinate, including a
  reversal, so the horizontal follow is proved to still work rather than proved
  to be non-`none`.

Two traps this repo has already paid for apply directly. `transform !== 'none'`
is satisfied by the start value and proves nothing — sample the path, not a
point. And the harness must not run inside the frames it measures: synthetic
`TouchEvent`s dispatched from a rAF callback reported 33.4ms where the real CDP
input path reported 16.7ms on the same build.

### 6. A pinned tab is given its own box — found by the browser, not predicted

This was not in the plan. The browser pass showed a card's `rect.top` dead
constant, which was the point, and its **width** jumping 172.5 → 187.5 on claim.

`.content.tab-leaving` and `.content.tab-entering.tab-pinned` pinned with
`left: 0; right: 0`. A fixed element does not inherit its container's padding, so
that is the viewport's width and not the tab's: claiming a gesture widened the
grid by both of `.container`'s paddings — **+20px, which `auto-fill` spends on
the cards, ~10px each at two columns** — and released it back.

**It predates this change, and the lift was hiding it.** Pinned at 390 and scaled
by 0.94, the tab rendered 366.6px wide against an in-flow 370: within 2px, so the
cards moved 172.5 → 176.25 and nobody saw it. One accident cancelling another.
Remove the scale and the full +20px is exposed, which would have shipped as the
next report — a grid that grows when a thumb lands is the same complaint as one
that drops, and this change's own spec says neither tab may change size.

So `pinTab()` writes `top`, `left` and `width`, from the rect
`beginTabTransition()` already reads before its first write. **No second
measurement**: the ~78ms forced-layout rule is intact, and the incoming tab has
no box of its own to read anyway — it is `display: none` until its class lands,
and it is a sibling in the same container, so the outgoing tab's box is its box.
The teardown clears all three, because an inline `width` that outlives the
gesture freezes the grid's column count through every resize after it.

The two tabs stay one viewport apart, so what shows between them mid-drag is a
gutter the width of the page's own padding — which is why decision 1's argument
about the scrim is stated the way it is, and not as "the panels tile the screen".

*Alternative considered:* leave it, on the grounds that it predates the change.
Rejected — it was invisible before only because of the thing being removed, so
"pre-existing" describes its origin and not its effect.

## Risks / Trade-offs

- **The windowing guard is deleted later as unexplained.** → Restated in the spec
  on the freeze rather than on the scale, rewritten in the code comment, and its
  test made unconditional so it fails loudly instead of passing vacuously.
- **The gesture loses its sense of depth and reads flatter.** → Accepted
  deliberately. The depth cost 23px of vertical movement in a horizontal gesture,
  and the viewer read the cost before they read the depth. Elevation and radius
  were already tried and removed for reasons of panel geometry that this change
  does not alter, so there is no cheap substitute waiting.
- **A subpixel seam between the two tiled panels.** → At fractional offsets the
  browser may leave a hairline between the outgoing and incoming tab, showing the
  page background. It is a hairline of the app's own background rather than of a
  scrim, it is transient, and the alternative (overlapping the panels) is the
  z-index bug that made TV Shows paint over Movies in both directions. Watch for
  it in the browser pass; do not fix it by overlapping.
- **`tokens.css` loses a long comment block that carries real history.** → The
  parallax-ratio note is independent of the lift and stays. The shadow/radius
  note is preserved, rewritten to explain why nothing at all is applied to a
  dragged tab rather than why the lift is only a scale and a scrim.
- **CLAUDE.md drifts.** → Its "SCALE AND A SCRIM" paragraph and the
  transform-origin lesson under it describe removed behaviour. Both are rewritten
  in the same commit as the code, per the project's docs gate.

## Migration Plan

None required. No stored state, no configuration, no `config.json` field, no
environment variable, no service worker cached asset semantics. The frozen
`docker-compose.yml` surface is untouched: same image name, same `9090:80`, same
volumes, same variable list, so `tests/test_compose_surface.py` is unaffected and
an existing user's compose file runs this unchanged.

Rollback is a revert of the commit. There is no data written by this behaviour to
undo.

## Open Questions

None. The one design choice — whether to keep a dimmed seam in place of the lift
— was put to the user and answered: remove the lift whole.
