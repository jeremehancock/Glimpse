## 1. The Actions tray

- [x] 1.1 Scope the `.sort-toggle` hide rule in `web/index.html` to the header:
      `.header-content .sort-toggle`. The unqualified selector is what empties
      the tray, whose body is itself a `.sort-toggle`.
- [x] 1.2 Keep that rule's breakpoint at `max-width: 992px`. Measured: with it
      removed the tabs row overflows `.header-content` at ≤850px and the search
      container collapses to 54px from 992px down. The header genuinely cannot
      hold those controls below ~992, so the page copy must keep withdrawing
      there.
- [x] 1.3 Move `.mobile-menu-button { display: flex; order: 3 }` from
      `max-width: 768px` up to `max-width: 992px`, so the tray's trigger arrives
      at the width the header controls withdraw. This is what closes the
      769–992px dead zone. Leave `.header-content .tabs` hiding at ≤768 — Movies
      and TV Shows fit at 769–992 and are worth keeping in the page.
- [x] 1.4 Confirm no other rule in `index.html` hides overlay content by an
      unqualified selector. The CDP sweep found only this one; re-check after
      editing.

## 2. The detail overlay's fixed region

- [x] 2.1 Wrap `.sheet__grip`, `.modal__head` and `.modal-header` in a single
      positioned container inside `.modal__panel`, and move `.modal-header` out
      of `.modal__body` so it becomes a sibling of the scroller rather than its
      first child.
- [x] 2.2 Give the panel explicit flex roles: `flex: 0 0 auto` on the fixed
      container, `flex: 1 1 auto; min-height: 0` on `.modal__body`.
- [x] 2.3 Cap the fixed container with a `max-height` in `vh` and let it scroll
      internally past the cap, so a long title on a short viewport can never
      squeeze the scrolling region to nothing.
- [x] 2.4 Apply the pin at both widths — no breakpoint-conditional structure. The
      desktop dialog's poster stops scrolling away; that is the intended change.
- [x] 2.5 Remove `.modal-header { margin-top: 40px }` from both media queries. It
      was clearance for a close `×` that is hidden on touch.

## 3. The backdrop artwork

- [x] 3.1 Reparent `.modal-backdrop-art` into the fixed container and give it
      `inset: 0`, replacing the fixed `height: 280px`. The art can then no longer
      extend past the fixed region for any content at any width.
- [x] 3.2 Fade the art out beneath the grab handle with
      `mask-image: linear-gradient(to bottom, transparent 0, black <grip-height>)`,
      paired with `-webkit-mask-image`. Keeps `top: 0` and the full-bleed look
      while leaving the handle legible.
- [x] 3.3 Verify an item with no backdrop artwork still renders the fixed region
      normally against the panel's own surface.

## 4. The drag gesture

- [x] 4.1 Add the fixed container to the gesture's opt-in selector list in
      `web/assets/overlays.js`, alongside `.sheet__grip`, `.sheet__head` and
      `.modal__head`.
- [x] 4.2 Confirm a tap on the trailer control inside the fixed region still
      activates it and does not dismiss — a zero-movement drag ends below the
      threshold.

## 5. Dead CSS

- [x] 5.1 Remove the three `.modal-body` (single-dash) rule blocks in
      `index.html`. The markup is `.modal__body`; these match nothing and imply
      the old layout is still live.

## 6. Tests

- [x] 6.1 Add a regression test asserting no `display: none` rule targets
      `.sort-toggle` without a `.header-content` ancestor. Demonstrate it fails
      against the current markup before committing.
- [x] 6.2 Add a regression test asserting `.modal-header` is not a descendant of
      `.modal__body`. Demonstrate it fails against the current markup first.
- [x] 6.3 Verify `test_drag_regions_are_not_the_scroller` still passes against
      the new structure, and extend it to assert the fixed container is a sibling
      of `.modal__body` and never an ancestor. If its regex no longer matches the
      markup, fix the regex — never relax the assertion.
- [x] 6.4 Add a test asserting the gesture's selector list in `overlays.js`
      resolves against classes that exist in the markup, in the manner of
      `test_openmodal_selectors_match_the_markup`.

## 7. Verification

- [x] 7.1 Drive a real browser over CDP — never `--virtual-time-budget`, which
      disables `requestAnimationFrame` and freezes every overlay shut. Assert at
      390px that the Actions tray's body has non-zero height and lists the sort,
      genre, server and install controls.
- [x] 7.2 Assert across 1280 / 1000 / 900 / 800 / 770 / 700 / 390px that at every
      width either the header controls or the hamburger is visible.
- [x] 7.3 At 390px and 1280px, open the detail overlay and assert the artwork's
      bottom does not exceed the fixed region's bottom, and that scrolling the
      body moves the summary while the poster's rect is unchanged.
- [x] 7.4 Confirm `openModal()`'s runtime insertions still land correctly — the
      date section into `.modal__body`, the retry button into `.modal-actions`.
- [x] 7.5 Check the fixed region on a short viewport (667px tall) with a
      multi-line title: the scrolling region must remain present and scrollable.
- [x] 7.6 Run `make lint` and `make test`. `make docker-smoke` is not required —
      nothing under `Dockerfile`, `config/` or the entrypoint changes.

## 8. Docs

- [x] 8.1 Check whether `README.md`, `docs/` or `CLAUDE.md` go stale. The CLAUDE.md
      overlay section describes the drag/scroll split and should record the fixed
      region as a third role. If nothing else is user-facing, say so explicitly
      rather than inventing edits.
- [x] 8.2 Update `docs/handover.md` — this is a third unarchived change waiting on
      the same `:dev` validation gate.

## 9. Physical device

- [ ] 9.1 Confirm on a real phone that a downward drag from the poster block
      dismisses, and that the handle reads clearly against a bright backdrop.
      Touch feel cannot be settled over CDP. (Synthesised touch events over CDP
      confirm the gesture fires and the thresholds behave; what a device adds is
      whether it *feels* right and whether the fade is enough contrast in
      daylight.)
