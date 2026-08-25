## 1. Tray choice presentation

- [x] 1.1 Confirm by grep that `.genre-item` has exactly two users — the genre
      tray via `genreItem()` and the server tray via `populateServerTray()`.
      Restyling a shared class changes both, which is the intent; knowing there
      is no third is the point of checking.
- [x] 1.2 Give `.genre-item` its own background, border and radius, sized as a
      touch target. Use `--surface-2` for the fill: the tray body is `--surface`,
      and `--surface-2` is the tier for a control sitting on a surface. Take the
      radius and the transition from existing tokens rather than new literals.
- [x] 1.3 Set its `display` explicitly. A `<button>` defaults to `inline-block`,
      which is what produces the ragged run — the entries must lay out as
      deliberate wrapping items, not as inline text.
- [x] 1.4 Lay the tray body out so the entries wrap within it and none overflows
      horizontally. `.genre-tray__body` and `.server-tray__body` have no rules at
      all today.
- [x] 1.5 Style `.genre-item__label` and `.genre-item__count`. Neither has a rule
      today, which is what produces `Action23`. The count is secondary: quieter
      colour, its own spacing, and no reserved space when it is empty —
      `genreItem()` writes an empty string when there is nothing to show.
- [x] 1.6 Give `.genre-item.active` a distinct appearance, and confirm
      `aria-pressed` still reflects it. A class alone is invisible to a screen
      reader; the builder already sets the attribute, so this is a check, not an
      addition.
- [x] 1.7 Verify the genre tray at 320px, 390px and 768px: entries wrap, nothing
      overflows, long names ("Science Fiction", "Martial Arts") do not break the
      row.
- [x] 1.8 Verify the server tray with three servers configured looks like the
      genre tray and shows no count.

## 2. The head divider

- [x] 2.1 Remove the head divider where it crosses artwork, scoped to
      `.modal__fixed .modal__head`. Do NOT remove it from the base `.modal__head`
      rule — it is correct on the trailer, the roulette and the server switcher,
      whose heads sit on flat surface.
- [x] 2.2 Leave `.modal-header`'s own `border-bottom` alone. It marks where the
      fixed region stops and the scrolling region starts, at the foot of the
      identity block, on surface rather than on artwork.
- [x] 2.3 Verify the detail overlay at a touch width and a pointer width: no line
      under the title, the region division still visible.
- [x] 2.4 Verify a flat-surface overlay still draws its divider.

## 3. The roulette as a tray

- [x] 3.1 Add the three regions the overlay system requires to the roulette
      panel: `.sheet__grip`, `.modal__head` and `.modal__body`. The spinner moves
      into the body. This is structural — the panel is currently a bare wrapper.
- [x] 3.2 Give the head a visible title and point the panel's accessible name at
      it, replacing the current `aria-label`.
- [x] 3.3 Add an `.overlay__close` to the head. The overlay has no close control
      at all today outside its error state, at any width.
- [x] 3.4 Add `.modal--tray-on-touch` to the overlay root. Do this AFTER the
      regions exist — the modifier hides the × on touch, so applying it to a
      panel with no grab handle produces an overlay that cannot be dismissed.
- [x] 3.5 Keep backdrop dismissal suppressed while it is choosing. The existing
      reasoning stands: a stray tap cancelling a pick the user just asked for
      reads as the control not working.
- [x] 3.6 Confirm the drag region and the scrolling region are separate elements.
      The head must not be nested inside the body — that hands the gesture back
      to the browser as a scroll, silently, with no visual difference on a
      desktop.
- [x] 3.7 Confirm the existing error state still works: its Close button, and the
      "nothing to pick" message.
- [x] 3.8 Verify on touch that the roulette rises from the bottom edge, spans the
      full width, and dismisses by dragging its handle.
- [x] 3.9 Verify on a pointer device that it is centred and closes with its ×.
- [x] 3.10 Confirm `aria-live="polite"` still announces the result now that the
      panel has a head above the spinner.

## 4. One dismissal per width

- [x] 4.1 Extend the rule that hides `.overlay__close` on touch to cover `.sheet`
      panels, not just `.modal--tray-on-touch`. A `.sheet` below the breakpoint
      is a tray by definition, and the existing comment's reasoning applies
      unchanged.
- [x] 4.2 Confirm the reciprocal holds: above the breakpoint the grip is hidden
      and the × is shown, so no width leaves an overlay with neither. This pair
      drifted apart once before, at 992px and 768px.
- [x] 4.3 Verify each tray at a touch width shows a handle and no ×, and at a
      pointer width shows a × and no handle.

## 5. Tests

- [x] 5.1 Add a test asserting the roulette panel carries a grip, a head and a
      body, and that the head is not nested inside the body.
- [x] 5.2 Add a test asserting every overlay panel has at least one dismissal
      affordance at each side of the touch breakpoint — the rule that hides one
      and the rule that shows the other must stay paired.
- [x] 5.3 Add a test asserting `.genre-item` declares a background, a border and
      an explicit display, and that `.genre-item__count` has a rule of its own.
      These are the properties whose absence produced the defect.
- [x] 5.4 Add a test asserting the head divider is scoped away from
      `.modal__fixed` but still present on the base rule.
- [x] 5.5 Mutate each new assertion to confirm it fails when the defect is
      reintroduced. A test that cannot fail is worse than no test — two in the
      sibling change passed against reintroduced defects until they were
      mutation-checked.
- [x] 5.6 Confirm `tests/test_overlay_markup.py` still passes: the roulette's
      panel must keep `role="dialog"`, `aria-modal="true"` and `tabindex="-1"`.

## 6. Documentation

- [x] 6.1 Record in `CLAUDE.md` that `.genre-item` is the shared tray-choice
      control, used by both the genre and server trays, and that a change to it
      lands in both.
- [x] 6.2 Record that an overlay presenting as a tray shows its handle and hides
      its close button, and that the two rules are a pair that must move
      together.
- [x] 6.3 Record that the roulette carries the three regions and why the modifier
      alone is not enough.
- [x] 6.4 Check whether `README.md` or `docs/` needs anything. If nothing
      user-facing changed, say so explicitly rather than inventing an edit.

## 7. Gates

- [x] 7.1 `make fmt`, then `make lint` and `make test` — both green. Note
      `make lint` needs Node 18+; a default `node` older than that fails ESLint
      with a config error rather than a lint error.
- [x] 7.2 Run the app in the container and look at every overlay at a touch width
      and a pointer width. This change is entirely visual, so the screenshot IS
      the verification.
- [ ] 7.3 Push to `dev` and validate the `:dev` image.
