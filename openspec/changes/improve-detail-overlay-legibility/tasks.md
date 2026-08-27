## 1. The artwork

- [x] 1.1 In `web/index.html`, change `.modal-backdrop-art`'s `opacity` from
      `0.35` to `0.10`.
- [x] 1.2 Delete both the `-webkit-mask-image` and the `mask-image` declarations
      from `.modal-backdrop-art`. Both, not one — the prefixed and unprefixed
      gradients are two separate masks and removing either alone leaves the fade
      in half the browsers.
- [x] 1.3 Rewrite the comment block above `.modal-backdrop-art`. Most of it
      explains the fade and would otherwise document a rule that no longer
      exists. Keep the `inset: 0` note (it records why the artwork is not a
      hardcoded height); replace the fade note with why the opacity is `0.10` —
      that it is the strongest artwork `--muted-text` clears 4.5:1 over against a
      fully white image, and that dimming the artwork moves the *handle's*
      background toward it, which is why the handle changed in the same commit.
- [x] 1.4 Leave `.modal__fixed .sheet__grip { position: relative; z-index: 1 }`
      alone. It is the paint-order half and is still required.

## 2. The grab handle

- [x] 2.1 In `web/assets/overlays.css`, change `.sheet__handle`'s `background`
      from `#4b4f57` to `#9aa0aa`.
- [x] 2.2 Comment the value at the rule: it clears 3:1 against both the panel
      surface and the detail overlay's artwork at its brightest, and it is one
      colour for every tray on purpose. Record that `#4b4f57` was below 3:1
      against plain surface on every tray — the mask had been hiding that in the
      only overlay anyone measured.

## 3. The dead tokens

- [x] 3.1 Delete `--grip-clear` and `--grip-height` from `web/assets/tokens.css`,
      including their comment blocks.
- [x] 3.2 Grep the whole repo for both names and confirm nothing reads them.
      Anything left is a reference to a token that no longer resolves, which CSS
      fails silently on.

## 4. The gap below the fixed region

- [x] 4.1 In `web/assets/overlays.css`, add
      `.modal__fixed + .modal__body { padding-top: 20px; }` next to the
      `.modal__body` rule.
- [x] 4.2 Comment it: `20px` matches the body's own horizontal inset; `+` and not
      `~` because the body is the immediate next sibling; and it is keyed on
      `.modal__fixed` rather than on the detail overlay so it states the real
      condition — a scrolling body with a pinned region above it.

## 5. Tests

- [x] 5.1 Add a shared contrast helper (sRGB relative luminance, the WCAG ratio,
      and an alpha-composite) for the two test files below to share. Two
      hand-copied curves drift, and the symptom is two tests disagreeing about
      the same pair.
      **Corrected while implementing:** this task said to point
      `tests/test_pill_contrast.py` at the helper too. That premise was wrong —
      the pill test computes no contrast at all. It is a source-shape test: it
      asserts the label colour is declared and that neither the fill nor the
      label is transitioned. There is no curve in it to share, so it is left
      alone. The helper went to a new `tests/contrast.py` rather than to
      `conftest.py`, which is for fixtures; pytest already puts `tests/` on the
      path, so both files import it plainly.
- [x] 5.2 Replace
      `test_overlay_layering.py::test_artwork_clears_past_the_handle_not_up_to_it`
      with a test that reads `.modal-backdrop-art`'s `opacity` and `--surface`
      and `--muted-text` from the CSS, composites white over the surface at that
      opacity, and asserts the muted text clears 4.5:1.
- [x] 5.3 In the same test file, assert `.modal-backdrop-art` declares no
      `mask-image` in either spelling.
- [x] 5.4 Replace
      `test_overlay_markup.py::test_the_backdrop_artwork_does_not_cover_the_grab_handle`
      with a test asserting `.sheet__handle`'s colour clears 3:1 against
      `--surface` **and** against the same white-over-surface composite. Both
      surfaces, in one test — the whole defect was a handle checked against one
      of them.
- [x] 5.5 Add a test asserting `--grip-clear` and `--grip-height` appear nowhere
      under `web/`, so the mask cannot come back by half.
- [x] 5.6 Confirm `test_grip_is_lifted_above_the_artwork` still passes unchanged.
- [x] 5.7 Check every other assertion touching `.modal-backdrop-art`,
      `.sheet__handle` or `.modal__body` across `test_overlay_layering.py`,
      `test_overlay_markup.py` and `test_tray_presentation.py` and update
      anything the edits above invalidate.

## 6. Gates and verification

- [x] 6.1 `make fmt` then `make lint` — prettier will have an opinion about the
      new CSS rule.
- [x] 6.2 `make test`.
- [x] 6.3 Open the app and check the detail overlay on an item with a **bright**
      backdrop and one with a dark backdrop, at a phone width and at a desktop
      width. Confirm: the year and metadata are comfortably readable on both; the
      artwork is still visibly there; the top edge is crisp with no fade and no
      band of bare surface; the Overview heading is clearly separated from the
      block above it.
- [x] 6.4 Open the genre tray, the Actions tray, the trailer overlay and the
      roulette overlay on a touch width and confirm the lighter handle looks
      right in each, and that none of them picked up the new top padding.
- [x] 6.5 Drag the detail tray down by its handle to confirm the gesture still
      dismisses — the grip and head keep `touch-action: none` and
      `.modal__fixed` must still not be a scroller.
- [x] 6.6 Check `README.md` and `docs/` for anything describing the overlay's
      artwork treatment. Nothing user-facing is expected to change; if nothing
      is stale, say so explicitly in the PR rather than inventing an edit.
- [x] 6.7 No `Dockerfile`, `config/` or entrypoint change, so no
      `make docker-smoke` is required — confirm that is still true at the end.
