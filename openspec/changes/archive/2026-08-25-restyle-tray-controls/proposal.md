## Why

The overlay system works and looks unfinished. The genre list renders as a ragged
run of default browser buttons — white boxes with counts jammed against their
labels, `Action23` — because the control became a `<button>` during the tray
conversion and no styling followed it. The server switcher reuses the same class
and inherited the same appearance. A divider cuts across the detail overlay's
artwork. The roulette is a centred box on a phone where every other overlay is a
tray. And the trays offer two ways to close where the project's own rule asks for
one.

None of this is broken, which is exactly why it needs a change of its own: it is
the difference between an app that works and an app that looks like it was
finished on purpose, and it is the last thing standing between the rewrite and a
validated `:dev` image.

## What Changes

- **Genre and server list items get a real presentation.** `.genre-item` is a
  `<button>` with a label and a count inside it, styled by a rule written for
  full-width `<div>` rows in a dropdown that no longer exists — so it falls back
  to the browser's own button chrome. It becomes a pill sized for a thumb, with
  the count as a distinct, quieter element rather than glyphs abutting the name.

- **The count is legible as a count.** `.genre-item__count` and
  `.genre-item__label` have no rules at all today. The count is secondary
  information and is styled as such, and it is absent rather than zero when the
  genre has no items.

- **The head divider comes off the detail overlay.** `.modal__head`'s
  `border-bottom` reads as a seam where it crosses the item's artwork. It stays
  on the overlays whose head sits on a flat surface, where it reads as intended.

- **The roulette becomes a tray on touch.** It is the only overlay still centred
  on a phone. It has no grab handle, no head and no body, so this is structural:
  it gains the three regions the overlay system requires, a title, and a close
  control it currently lacks at every width outside its error state.

- **A tray offers one way to close on touch.** `.overlay__close` is hidden below
  the touch breakpoint on `.sheet` panels, matching what `.modal--tray-on-touch`
  already does. Two dismissals, one of them a small target in the corner
  furthest from a thumb, is worse than one that is obvious.

No behavior changes: every control does what it already did. There is no
**BREAKING** change.

## Capabilities

### New Capabilities

None. This is presentation for capabilities that already exist.

### Modified Capabilities

- `genre-filter`: the genre tray's items are presented as tappable choices with a
  secondary count, rather than as unstyled buttons.
- `multi-server`: the server switcher's destinations are presented the same way,
  since they share the control.
- `visual-design`: a tray offers a single dismissal on touch; a head divider is
  not drawn where it crosses artwork.
- `roulette`: the overlay is a tray on touch and a dialog on a pointer device,
  and carries a title and a close control.
- `media-detail`: no divider under the item's title.

## Impact

- `web/index.html` — the `.genre-item` rules and new rules for its label and
  count; the roulette overlay's markup and its stylesheet block; the head border
  in the detail overlay.
- `web/assets/overlays.css` — the touch block gains the rule hiding a tray's ×;
  the head border becomes scopable.
- `tests/` — assertions for the roulette's three regions and for the single
  dismissal affordance. `tests/test_overlay_markup.py` already asserts every
  panel carries `role`, `aria-modal` and `tabindex`; the roulette's new head must
  not break it.

**The frozen `docker-compose.yml` surface is NOT touched.** No environment
variable is added, removed or reinterpreted. An existing user's compose file runs
this unmodified.

Nothing under `web/` is built, so there is no asset pipeline to update. This
change touches no file that ships outside `/app/web`, so `make docker-smoke` is
not strictly required — but the roulette markup change is worth one look in the
container before the image is cut.
