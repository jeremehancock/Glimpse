## 1. Remove the lift from the stylesheet

- [x] 1.1 In `web/index.html`, change the `.content.tab-leaving, .content.tab-entering` rule's transform to `translateX(var(--tab-shift, 0))` and delete the `transform-origin` declaration. Leave `display`, `will-change` and the `z-index` rule alone.
- [x] 1.2 Delete the `.tab-dragging::after` scrim rule.
- [x] 1.3 Rewrite the comment above the transform: keep the horizontal-only rule and the reason for it, drop the "one exception" paragraph, and fold in why nothing else is applied to a dragged tab — a panel over a million pixels tall shows neither end on screen, so a shadow renders as a band tracking the thumb and a radius renders nothing. Keep the note that these panels' height is a *visible* hazard and not only an arithmetic one.
- [x] 1.4 In `web/assets/tokens.css`, delete `--tab-drag-lift` and `--tab-drag-scrim`. Keep `--dur-tab-settle-min`.
- [x] 1.5 Rewrite the tab-drag comment block in `tokens.css`: keep the no-parallax-ratio paragraph and the settle-floor paragraph verbatim, replace the lift paragraphs with a short note that a dragged tab is translated and nothing else, and why.

## 2. Remove the lift from the gesture code

- [x] 2.1 Delete `const TAB_LIFT = readToken('--tab-drag-lift', 0.94);`.
- [x] 2.2 Reduce `pinTab(panel, viewportTop, middle)` to `pinTab(panel, viewportTop)`: drop the `--tab-origin-y` write and the `middle` parameter, and replace its comment block with a one-line statement of what it does.
- [x] 2.3 In `beginTabTransition()`, drop the `lifted` parameter, the `viewportMiddle` computation, the `if (lifted) { … }` block that adds `tab-dragging` and sets `--tab-lift` on both panels, and update both `pinTab()` calls. Verify the single `getBoundingClientRect()` still sits above every write in the function.
- [x] 2.4 Update both `beginTabTransition()` call sites to the new arity — the slide-from-rest call that passed `false` and the drag call that passed `true`.
- [x] 2.5 In `beginResistedDrag()`, drop `viewportMiddle`, the `--tab-lift` set, and `tab-dragging` from the `classList.add`, keeping `tab-transitioning`. Update its `pinTab()` call and its comment, which currently says "pinned and lifted".
- [x] 2.6 In `settleTabDrag()`, delete the `--tab-lift` reset to `'1'` and the comment about the lift releasing over the settle. Keep the `--dur-tab-settling` write and the `tab-sliding` class.
- [x] 2.7 In `endTabTransition()`, delete the `--tab-lift` and `--tab-origin-y` `removeProperty` calls and drop `tab-dragging` from the root `classList.remove`, keeping `tab-transitioning`.
- [x] 2.8 Grep `web/` for `tab-lift`, `tab-drag-lift`, `tab-drag-scrim`, `tab-dragging`, `tab-origin-y` and `TAB_LIFT` and confirm zero hits outside `alpine.min.js`.

## 3. Re-ground the windowing refusal

- [x] 3.1 Rewrite the comment on `updateGridWindow()`'s gesture refusal so it rests on the freeze — a pinned tab sits at a captured offset, not at the viewer's scroll position — rather than on a scale that no longer exists. Do not weaken it to "a pinned tab receives no scroll events".
- [x] 3.2 Confirm the refusal itself is unchanged in behaviour: no code path may compute a window while `tabTransition` is live.

## 4. Update the tests

- [x] 4.1 Rewrite `test_the_lift_is_paired_with_a_windowing_refusal` to assert the refusal unconditionally, removing the `if 'scale(' not in rule: return` early exit that would make it pass vacuously.
- [x] 4.2 Rewrite `test_a_scaled_tab_anchors_its_origin_to_the_viewport` to assert the tab transform is a horizontal translate only — no `scale(`, no `transform-origin` — and rename it to say that.
- [x] 4.3 Rewrite `test_the_lift_is_a_scale_and_a_scrim_only` to assert the lift is gone and nothing replaced it: no `--tab-drag-lift`/`--tab-drag-scrim` tokens, no `tab-dragging` class, no `box-shadow` or `border-radius` on the tab rules. Rename it accordingly and carry its reasoning into the docstring.
- [x] 4.4 Remove `--tab-drag-lift` and `--tab-drag-scrim` from the token-ownership test's list and drop its `readToken('--tab-drag-lift'` assertion; keep `--dur-tab-settle-min`.
- [x] 4.5 Remove `--tab-lift` from the teardown test's list of properties that must be cleared, and add `--tab-origin-y` nowhere — both are gone from the code.
- [x] 4.6 Re-read `tests/test_tab_transition.py` end to end for any other assertion that names the lift, the scrim or the origin.

## 5. Update the documentation

- [x] 5.1 In `CLAUDE.md`, replace the "The lift is a SCALE AND A SCRIM" bullet with one stating that a dragged tab is translated horizontally and given nothing else, and why: the scale displaced the grid ~23px vertically on a phone and was reported as the grid dropping.
- [x] 5.2 In `CLAUDE.md`, rework the `transform-origin` sub-bullet — the +36,791px story and the "two symptoms" lesson. Keep the lesson that a transform on a panel this tall is a visible hazard as well as an arithmetic one; drop the instruction to set `transform-origin` per gesture, which is no longer code that exists.
- [x] 5.3 In `CLAUDE.md`, fix the "Horizontal translate only — and the lift's `scale` is the ONE exception, which costs TWO safeguards" bullet: there is no exception now. Keep safeguard 1 (the windowing refusal, restated on the freeze) and remove safeguard 2.
- [x] 5.4 Check `README.md` and `docs/` for any description of the swipe's appearance. If nothing user-facing changed there, say so explicitly in the commit rather than inventing edits.

## 6. Give a pinned tab its own box

Added during verification. The browser pass showed a card's width jumping
172.5 → 187.5 on claim: the pin used `left: 0; right: 0`, which is the viewport's
width rather than the tab's, so the grid widened by `.container`'s padding. It
predates this change and the lift's scale was cancelling it to within 2px.

- [x] 6.1 Collapse the two pinned rules into one `position: fixed` selector list and delete `left: 0; right: 0` from both.
- [x] 6.2 Widen `pinTab()` to `(panel, viewportTop, left, width)`, writing all three inline.
- [x] 6.3 In `beginTabTransition()` and `beginResistedDrag()`, keep the single pre-write `getBoundingClientRect()` in a `box` local and pass `box.left`/`box.width`. Pin the incoming tab from the outgoing tab's box — it is `display: none` and has none of its own, and a second read would be a forced layout on the opening frame.
- [x] 6.4 Clear `left` and `width` alongside `top` in `endTabTransition()`.
- [x] 6.5 Add `test_a_pinned_tab_keeps_its_own_horizontal_box`, and confirm it FAILS against the `left: 0; right: 0` form before keeping it.

## 7. Verify

- [x] 7.1 `make lint` and `make test` both pass. (`make lint`'s JS half needs Node 18 on PATH; the shell's default is 16 and eslint's config load fails there before reading a file.)
- [x] 7.2 Serve `web/` and drive a real drag over CDP at a phone viewport with `Browser.drag()`. Sample a card's `getBoundingClientRect()` at each coordinate and assert `top` is constant within a pixel across the whole gesture, including the frame the axis lock is crossed. This is the reported bug, measured. **Before: 85.00 → 105.22 on claim, +20.22px. After: 85.00 flat, spread 0.00px.**
- [x] 7.3 In the same pass assert `width` is constant (no scale) and `left` corresponds to the finger at every sampled coordinate, including a reversal — a handler writing a constant offset passes any single-point check. **Width spread 0.00px, scale exactly 1 on every frame, translate deviation 0.00px over 5 samples including the reversal.**
- [x] 7.4 Confirm by eye and by measurement that no dim appears behind the tabs at any offset, and that no visible seam of background persists between them. **Root `::after` is `content: none`, `rgba(0,0,0,0)` throughout; before, it was `rgba(0,0,0,0.28)`. The tabs stay exactly one viewport apart, so what shows between them is the page's own padding gutter.**
- [x] 7.5 Exercise the other paths at the same viewport: a commit by distance, a commit by flick, an abandon, a resisted drag off each end, a `touchcancel` mid-drag, and a tab change from the tab buttons. Each resolves with the page scrollable and the grid re-windowing. **All clean. The flick had to be read from the app's own drag record: over CDP each touch is a blocking round-trip, so a short path delivers 0.44 px/ms against a 0.5 threshold and fails to commit for the driver's reasons, not the app's. Measured at the release: 120px of travel — under the 130px distance threshold — at −1.32 px/ms commits.**
- [x] 7.6 Scroll deep into a large library, drag, abandon, and confirm the viewer is returned to the scroll offset the gesture started from. **30,000px → 30,000px, first rendered card index 162 → 162.**
- [x] 7.7 Repeat at 1280px: the drag does not run there, but the same freeze does. **Tab switch clean, nothing pinned, no inline box left behind.**
- [x] 7.8 `openspec validate remove-tab-drag-lift --strict` passes.
