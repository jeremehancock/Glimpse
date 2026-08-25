## Why

Five overlays wear the same grab handle and hold their titles three different
distances below it. Measured in a real browser at 390×844:

| Overlay | Head | Handle bottom → title glyphs |
| --- | --- | --- |
| Actions, Genre, Switch server | `.sheet__head` | **18.4px** |
| Detail | `.modal__head` | **16.88px** |
| Roulette | `.modal__head` | **20.4px** |

A 3.5px spread across overlays that open one after another from the same screen.
Nothing is broken and nothing errors — it reads as the trays being slightly
unsettled relative to each other, which is the failure mode a design system
exists to prevent.

`.sheet__title` in `web/assets/overlays.css` already carries the rule this
violates, in a comment: *"A tray and a dialog wear the same grab handle, so they
must hold their titles the same distance below it… line-height is inherited
rather than set for that reason — restoring an override here is the edit most
likely to undo this quietly."* The rule was written down and never enforced.

## What Changes

Two independent causes, which is why neither was caught:

- **The padding half.** `.sheet__head` sets `padding-top: 14px`, `.modal__head`
  sets `16px`. Nothing intends this; the two heads are otherwise identical
  boxes.
- **The half-leading half.** `.modal-title` sets `line-height: 1.1` — exactly
  the override the comment warns against. At `1.1rem` that pulls the glyphs
  3.52px up inside their line box, against the `1.5` every other title inherits.

They partly cancel on the detail overlay (+2 padding, −3.52 leading ≈ −1.5px net)
and compound on the roulette (+2, −0). That is why the error never presented as
a clean 2px offset anyone would think to look for.

- Give `.sheet__head` and `.modal__head` the same vertical padding; they keep
  their different horizontal padding, which matches each shape's body.
- Stop `.modal-title` overriding `line-height`.
- Delete the rest of `.modal-title`'s type declarations, which are **dead**:
  `font-size: 2.2em`, `font-weight: 700`, `margin` and `color` are all
  outranked by `.modal__head h2` (0-1-1 beats 0-1-0). So are the two media-query
  `font-size` overrides at 768px and 480px. The rule reads as the thing that
  sets the detail title's type and sets none of it — which is why an unwanted
  `line-height` sat there unnoticed.
- Key the pointer-width padding bump to heads that actually have a grip above
  them, so it lands on every overlay that loses a handle and not on the trailer,
  which never had one.
- Pin the invariant with a test, so the comment stops being the only thing
  holding it.

No behavior, no markup, no JavaScript. **The frozen `docker-compose.yml` surface
is untouched** — no environment variable, port, volume or image name is involved.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `visual-design`: adds a requirement that every overlay hold its title the same
  distance below the grab handle, measured to the glyphs rather than to the line
  box.

## Impact

| Area | Change |
| --- | --- |
| `web/assets/overlays.css` | `.sheet__head` / `.modal__head` vertical padding; the pointer-width bump |
| `web/index.html` | `.modal-title` reduced to what it actually controls; two dead media-query rules removed |
| `tests/test_tray_presentation.py` | New tests pinning equal head padding and no title `line-height` override |

Visually: the three trays' titles move down ~2px, the detail title down ~3.5px,
the roulette title up ~2px. The detail overlay's `.modal__fixed` region grows for
a title long enough to wrap, because the restored `1.5` line-height makes each
line taller — that region is bounded by clamping the title, not by a scrollbar,
so the cap still holds, but the 3-line worst case needs re-checking at 390px.
