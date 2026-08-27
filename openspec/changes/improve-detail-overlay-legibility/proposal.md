## Why

The detail overlay paints the item's title, year, content rating and duration on
top of that item's backdrop artwork, and the artwork is currently strong enough
that the text competes with it. The year and the metadata pills are the worst of
it — a light grey on a picture, at a contrast that depends entirely on which item
was opened. The picture is meant to be texture behind the identity block, not a
second thing to read.

Two smaller complaints come with it: the artwork is faded out across its top
edge, which reads as a smudge on an otherwise crisp panel; and the Overview
heading starts immediately under the line that divides the pinned identity block
from the scrolling content, so the two run together.

This change touches no Python, no configuration, and no part of the frozen
`docker-compose.yml` surface — it reads no environment variable and adds none.
An existing user's compose file is unaffected.

## What Changes

- **The item's backdrop artwork is rendered much fainter.** It drops far enough
  that the dimmest text drawn over it clears a normal reading-contrast bar even
  against a fully white backdrop image — so legibility stops being a property of
  which item the user opened. The artwork still reads as texture behind the
  identity block, which is all it was ever for.
- **The fade across the top of the artwork is removed.** The artwork now reaches
  the panel's top edge at full strength.
- **The grab handle carries its own contrast instead.** Removing the fade takes
  away the only thing keeping the handle distinguishable from bright artwork, so
  the handle is lightened to a value that clears the non-text contrast bar over
  both the panel's own surface and the faintest-possible-artwork worst case. This
  is a change to the shared handle, so every tray gets it — the handle is one
  control and styling the detail overlay's copy apart is how the two drift.
  It is also an improvement on flat surface, where the current handle does not
  clear that bar either.
- **The two tokens that existed only to describe the fade — `--grip-clear` and
  `--grip-height` — are deleted.** With the fade gone they have no reader. A
  token nothing consumes is the kind of live-looking dead code this project has
  shipped before.
- **The scrolling region gains a gap below the division.** The Overview heading
  no longer begins flush against the border under the poster and metadata.

What deliberately does **not** change: the artwork still fills the fixed region
and reaches the panel's top edge (no band of bare surface above it); the handle
is still drawn above the artwork by paint order; and the border between the fixed
and scrolling regions stays.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-detail`: the requirement that the artwork be faded out behind the grab
  handle is replaced by a requirement on the artwork's strength — it must be
  faint enough that text over it is legible against any item's image — plus a
  requirement that the scrolling region is separated from the fixed region by a
  visible gap.
- `visual-design`: the grab handle gains a requirement that it be legible by its
  own contrast against every surface it can be drawn over, rather than relying on
  whatever is behind it being cleared away.

## Impact

- `web/index.html` — the `.modal-backdrop-art` rule (opacity, and the two
  `mask-image` declarations); the comment block above it, which currently
  explains the fade at length and would otherwise document a rule that no longer
  exists.
- `web/assets/overlays.css` — `.sheet__handle`'s colour, and a new rule giving a
  `.modal__body` that follows a `.modal__fixed` some top padding.
- `web/assets/tokens.css` — `--grip-clear` and `--grip-height` removed.
- `tests/test_overlay_layering.py` and `tests/test_overlay_markup.py` — both
  currently assert the fade exists and that the tokens are declared. Those
  assertions are replaced by contrast assertions, computed the way
  `tests/test_pill_contrast.py` already computes them, so the numeric decisions
  are pinned rather than merely written down.
- No Python source, no `Dockerfile`, no `config/`, no snapshot format. No
  `make docker-smoke` needed.
