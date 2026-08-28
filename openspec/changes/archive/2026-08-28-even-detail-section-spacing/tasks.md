## 1. The shared separation

- [x] 1.1 Add `--overlay-section-gap: 24px` to `:root` in `web/assets/tokens.css`,
  with a comment stating what it governs: one break value for an overlay body —
  between two sections, and below the division under a pinned region — and that a
  heading stands half that distance from the block it introduces, so a heading
  always groups downward. Say why it is here rather than in `index.html`: two
  rules in two files have to agree about it.
- [x] 1.2 In `web/assets/overlays.css`, change `.modal__fixed + .modal__body`'s
  `padding-top: 20px` to `var(--overlay-section-gap)`. Rewrite the paragraph in
  that rule's comment that justifies 20px as matching the body's horizontal
  inset: the number now comes from the body's section rhythm, because the border
  is the heaviest division in the body and may not be its smallest gap. Keep the
  rest of the comment — why it is keyed on `.modal__fixed` rather than on the
  detail overlay, and why `+` rather than `~`.

## 2. The body's rhythm

- [x] 2.1 In `web/index.html`, delete the `.modal-section { margin-bottom: 5px }`
  rule and replace it with `.modal-section + .modal-section { margin-top:
  var(--overlay-section-gap) }`. Comment it with both reasons: the gap belongs
  between siblings so the body's own `padding-bottom` stays the only thing under
  the last section, and an adjacent-sibling selector reaches the Date Added
  section `openModal()` appends without it carrying a marker.
- [x] 2.2 In the same file, give `.modal-section-title` `line-height: 1.3` and
  change its `margin-bottom: 15px` to `calc(var(--overlay-section-gap) / 2)`.
  Comment the leading — a rule that sets a heading's type must set all of it, and
  the leading a heading inherits is half-inside every gap around it — and comment
  the `calc()`: the relation is the decision, so it is written in the code rather
  than as a second token that can be edited on its own.
- [x] 2.3 Add the `.modal-prose` rule: a local `--prose-leading: 1.7`,
  `line-height: var(--prose-leading)`, and `margin-block: calc((1 -
  var(--prose-leading)) * 0.5em)`. Comment what it is for (bare text leaves the
  same gap as a filled block because its half-leading is withdrawn), why the trim
  is derived rather than written as `-0.35em` (a literal is a second copy of the
  leading, and drift is silent), and what it depends on — margin collapsing
  through `.modal-section`, so that element must never gain padding, a border, or
  its own formatting context.
- [x] 2.4 Delete the `.summary-section` rule and remove the class from the
  markup. Its `line-height` has moved to `.modal-prose` and its `color` restates
  what `body` already sets. Confirm with `grep -rn summary-section web/ tests/
  tools/ scripts/` that nothing else refers to it before removing it.

## 3. Applying the prose class

- [x] 3.1 Add `class="modal-prose"` to `#modal-summary` in the detail overlay's
  markup.
- [x] 3.2 In `openModal()`, add `class="modal-prose"` to the `#modal-added-date`
  div in the appended Date Added section.
- [x] 3.3 In `openModal()`, add `class="modal-prose"` to the two placeholder
  divs — `No genres available` and `No cast information available`. They are bare
  text in a slot that normally holds pills or cards, so without the class they
  are the one path where the rhythm goes back to being uneven, and it is the path
  nobody sees.

## 4. Pinning the decisions

- [x] 4.1 Add `tests/test_detail_spacing.py`, following the helper style in
  `tests/test_tray_presentation.py` (`strip_comments`, `css_rules`, `css_block`,
  module-scoped fixtures). Open it with a docstring saying what the file can and
  cannot check: CI has no browser, so it pins the relations that would otherwise
  drift, and the pixels are verified by hand.
- [x] 4.2 Assert `--overlay-section-gap` is declared once in `tokens.css` and is
  read by both `.modal__fixed + .modal__body` in `overlays.css` and
  `.modal-section + .modal-section` in `index.html` — the cross-file agreement is
  the reason it is a token.
- [x] 4.3 Assert no rule gives `.modal-section` a `margin-bottom`, so the
  inverted rhythm cannot come back by the route it arrived on, and the body's
  trailing space stays the body's padding.
- [x] 4.4 Assert `.modal-section-title` declares its own `line-height`, and that
  its `margin-bottom` is expressed as a `calc()` over `--overlay-section-gap`
  rather than as a literal — a heading may not sit at a distance chosen
  independently of the separation around it.
- [x] 4.5 Assert no `.summary-section` rule exists and the class appears nowhere
  under `web/`.
- [x] 4.6 Assert the `.modal-prose` block declares `--prose-leading` and that
  both its `line-height` and its `margin-block` reference it, so the trim cannot
  drift from the leading it is trimming.
- [x] 4.7 Assert every bare-text block in the detail body carries `.modal-prose`:
  `#modal-summary` in the markup, and the Date Added value and both placeholder
  strings in `openModal()`.
- [x] 4.8 Run `make fmt`, then `make lint` and `make test`. Both gates must pass.

## 5. Verifying it in a browser

- [x] 5.1 Open the detail overlay for an item that has a multi-paragraph summary,
  several genres and a full cast. Measure, in DevTools, the three gaps between
  sections — summary to Genres, pills to Cast, cards to Date Added — and confirm
  they are equal. This is the assertion `make test` cannot make.
- [x] 5.2 Measure the four heading-to-content gaps and confirm they are equal to
  each other and visibly smaller than the section gaps, so each heading groups
  with the content beneath it.
- [x] 5.3 Confirm the distance from the division under the identity block to the
  Overview heading equals a section gap, and that the space below the last line
  of the body equals the body's 20px horizontal inset.
- [x] 5.4 Check the two paths that only exist for sparse items: an item with no
  genres and an item with no cast. The placeholder line must leave the same gaps
  the pills or cards did.
- [x] 5.5 Check the same measurements at a touch width (the tray shape) and below
  600px, where `.modal-section-title` drops to `1.1em`. The gaps are absolute and
  the leading is unitless, so the rhythm should hold; confirm it does rather than
  assuming it.
- [x] 5.6 Confirm nothing about the overlay's behaviour moved: the downward drag
  still dismisses it on touch, the body still scrolls under the pinned identity
  block, and the trailer button still opens the trailer.

## 6. Documentation

- [x] 6.1 Add the two rules to `CLAUDE.md`'s overlay section, in the same
  commit: a heading stands nearer to what it introduces than to what precedes it,
  with the derived-from-one-token mechanism; and bare prose withdraws its own
  half-leading so a text-ended block and a box-ended block leave the same gap,
  with the note that this rides on margin collapsing through `.modal-section`.
  Both are invisible in a diff and both are easy to undo by accident.
- [x] 6.2 Check `README.md` and `docs/` for anything describing the detail
  overlay's layout. If nothing user-facing changed, say so explicitly in the PR
  rather than inventing edits.
