## 1. Unify the two head rules

- [x] 1.1 In `web/assets/overlays.css`, merge the shared box of `.sheet__head`
      and `.modal__head` into one selector list: `flex`, `display`,
      `align-items`, `justify-content`, `gap`, `border-bottom`, `margin-bottom`,
      `touch-action`, and vertical padding of `14px` top / `12px` bottom. Leave
      each shape a rule of its own carrying only its horizontal inset — 16px for
      the tray, 20px for the dialog, each matching its body.
- [x] 1.2 Comment the merged rule with why the vertical padding is shared: the
      two heads sit the same distance below the same grab handle, and equal
      padding is only half of that — see the `.sheet__title` comment for the
      other half.
- [x] 1.3 In the `@media (min-width: 768px)` block, replace the `.sheet__head`
      padding bump with `.sheet__grip ~ .sheet__head, .sheet__grip ~ .modal__head
      { padding-top: 18px }`. Comment that `~` and not `+` is required because
      `.modal-backdrop-art` sits between the detail overlay's grip and its head,
      that the rule depends on the grip remaining a sibling, and that it stays
      inside this media query because a sibling selector matches a
      `display: none` grip.
- [x] 1.4 Confirm `.modal__head`'s bottom padding did not change (it was already
      12px) and that the trailer, which has no grip, keeps `padding-top: 14px`
      at every width.

## 2. Stop the detail title overriding its line-height

- [x] 2.1 Re-grep `.modal-title` across `web/` to confirm it appears in the
      markup only inside a `.modal__head`, so `.modal__head h2` matches wherever
      it does. If it appears anywhere else, stop and re-derive the specificity
      before deleting anything.
- [x] 2.2 Delete the `.modal-title` rule in `web/index.html`. All five
      declarations are dead or unwanted: `margin`, `font-size`, `font-weight`
      lose to `.modal__head h2` at (0,1,1) vs (0,1,0), `color` restates the
      inherited value, and `line-height: 1.1` is the defect.
- [x] 2.3 Delete the two dead `.modal-title { font-size }` overrides in the
      ≤768px and ≤480px media queries — same specificity, same loss.
- [x] 2.4 Leave `.modal__fixed .modal-title` untouched. Its line clamp is what
      bounds the fixed region, and it is a separate rule.

## 3. Pin the invariant

- [x] 3.1 Add a test to `tests/test_tray_presentation.py` asserting the tray head
      and dialog head declare equal top padding and equal bottom padding, so a
      future edit to one has to touch the other.
- [x] 3.2 Add a test asserting no rule in `web/index.html` or
      `web/assets/overlays.css` sets `line-height` on an element serving as an
      overlay title (`.sheet__title`, `.modal__head h2`, `.modal-title`,
      `#roulette-title`, `#detail-title`). Name the reason in the assertion
      message: the gap is measured to the glyphs, so half-leading is part of it.
- [x] 3.3 Add a test asserting the pointer-width padding bump names both heads
      and uses `~`, with a message saying `+` misses the detail overlay.
- [x] 3.4 Add a test asserting the bump lives in the same media query that hides
      the grip, so the two cannot drift to different breakpoints.

## 4. Verify in a real browser

- [x] 4.1 With a seeded container running, use `tools/browser.py` at 390×844 to
      measure handle-bottom → title-glyph for Actions, Genre, Switch server,
      Detail and Roulette. All five must read **18.4px**.
- [x] 4.2 Repeat at 1280×900, measuring panel-top → title-glyph. All five must
      read the same number, and the trailer must be unchanged from before the
      change.
- [x] 4.3 Confirm the detail title still computes to `font-size: 17.6px` and
      `font-weight: 600` after `.modal-title` is deleted.
- [x] 4.4 At 390×844, open the detail overlay on an item whose title wraps to 3
      lines and confirm `.modal__fixed` still leaves the scrolling body usable
      height. If it does not, reduce the clamp in `.modal__fixed .modal-title`
      to 2 lines — never add `overflow` to `.modal__fixed`.
- [x] 4.5 Confirm the grab handle is still legible over the detail overlay's
      backdrop artwork: `.modal-backdrop-art`'s mask reads `--grip-clear` and
      `--grip-height`, which this change does not touch, but the head moved
      relative to it.

## 5. Gates and docs

- [x] 5.1 Run `make fmt`, then `make lint` and `make test`; both must pass.
- [x] 5.2 No `Dockerfile`, `config/` or entrypoint change is involved, so
      `make docker-smoke` is not required — confirm that is still true before
      skipping it.
- [x] 5.3 Check whether `CLAUDE.md`'s overlay-system section should record that
      overlay titles never set `line-height` and that the two heads share their
      vertical padding. If it should, edit it in the same commit; if not, say so
      explicitly.
