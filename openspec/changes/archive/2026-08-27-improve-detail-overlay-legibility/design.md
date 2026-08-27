## Context

The detail overlay's fixed region — grab handle, title bar, poster, year, rating,
duration, trailer button — is drawn over `.modal-backdrop-art`, an absolutely
positioned `div` filling that region with the item's backdrop image. Today it is
`opacity: 0.35`, with a two-declaration `mask-image` gradient that holds the
artwork fully transparent for `--grip-clear` (23px) and then ramps it to opaque
over a further `--grip-height` (17px), so the grab handle never sits on a
picture.

The complaint, measured. Composite a fully white backdrop over the panel surface
`#2a2a2a` at `opacity: 0.35` and you get `#757575`. The two pieces of text most
often on top of it — `.modal-year` and the `.metadata-item` pills — are
`--muted-text: #aaa`.

| Text | Over `#757575` |
| --- | --- |
| `--muted-text` `#aaa` (year, rating, duration) | **2.00:1** |
| `--light-text` `#fff` (title) | 4.64:1 |

2.00:1 is roughly half the 4.5:1 a body-text bar asks for. The title survives
because it is white; the metadata does not. That matches the report exactly — the
overlay does not look broken, it looks like the small print has gone soft, and
only on some items.

Three things are being asked for, and they are not three independent tweaks: the
fade exists *because* the artwork is strong, so removing the fade and weakening
the artwork have to be reasoned about together, and the grab handle is the thing
caught between them.

## Goals / Non-Goals

**Goals:**

- Text over the item's artwork is legible for every item in a user's library, not
  for the average one.
- The artwork reaches the panel's top edge at one uniform strength, with no fade.
- The grab handle stays a usable affordance on touch, where it is the only way to
  dismiss the tray by gesture.
- The Overview heading is visibly separated from the identity block above it.

**Non-Goals:**

- Re-theming the overlay, changing `--muted-text`, or restyling the metadata
  pills. The relation between text and background is being fixed from the
  background side, which is the side that was wrong.
- Removing the backdrop artwork. It is texture behind the identity block and it
  stays.
- Touching any other overlay's layout, the drag gesture, the focus manager, or
  the scroll lock.
- Anything in Python, `config/`, the `Dockerfile`, or `docker-compose.yml`.

## Decisions

### 1. `opacity: 0.35` → `0.10`, derived from the contrast bar rather than picked

`0.10` is not a taste judgement. It is the **strongest** artwork that still lets
`--muted-text` clear 4.5:1 against a fully white image:

| Artwork opacity | Composite bg | `#aaa` over it |
| --- | --- | --- |
| 0.35 (today) | `#757575` | 2.00:1 ✗ |
| 0.20 | `#555555` | 3.23:1 ✗ |
| 0.15 | `#4a4a4a` | 3.82:1 ✗ |
| 0.12 | `#444444` | 4.22:1 ✗ |
| **0.10** | **`#3f3f3f`** | **4.51:1 ✓** |
| 0.08 | `#3b3b3b` | 4.82:1 ✓ |

The margin at 0.10 is deliberately thin — one step further and the artwork is
being dimmed past what the requirement asks for, which throws away picture for
nothing. The thin margin is also what makes the pinning test worth having: any
later change to `--muted-text`, to the surface colour, or to this opacity fails
it immediately rather than drifting a few points at a time.

**Worst case, not typical case.** The image behind the text is chosen by the
user's library. A number tuned against a representative backdrop is a number that
fails for somebody, and it fails invisibly — the person who opened *that* item
has no way to know the app meant something else. Same reasoning the repo already
applies to the pill contrast.

**Alternative considered — keep 0.35 and lighten the metadata to `#fff`.**
Rejected. It flattens the identity block's hierarchy (year and rating would read
as loudly as the title), it leaves the *next* thing anyone puts over the artwork
just as unreadable, and it does not address what the user actually said, which is
that the picture is too strong.

**Alternative considered — a gradient scrim under the text only.** Rejected: that
is a second masked layer over the artwork, which is the thing being removed. It
also has to know where the text is, so it breaks the moment the identity block's
layout changes.

### 2. Delete the mask outright; the handle carries its own contrast

Both `mask-image` declarations go, and so do `--grip-clear` and `--grip-height` —
the mask was their only reader, and a token nothing consumes is exactly the
live-looking dead code this repo has shipped before.

The paint-order half stays. `.modal__fixed .sheet__grip { position: relative;
z-index: 1 }` is what puts the handle *above* the artwork at all; the artwork is
positioned and the grip is not, so without it the artwork covers the handle
whatever the mask says. That rule and its test are untouched.

What the mask was providing is contrast, and **lowering the artwork's opacity
makes that worse, not better** — the current handle `#4b4f57` is a mid-grey, and
dimming the artwork moves the background *toward* it:

| Handle | vs. panel surface `#2a2a2a` | vs. white artwork @ 0.10 (`#3f3f3f`) |
| --- | --- | --- |
| `#4b4f57` (today) | 1.75:1 ✗ | 1.28:1 ✗ |
| `#8b909a` | 4.48:1 ✓ | 3.27:1 ✓ |
| **`#9aa0aa`** | **5.46:1 ✓** | **3.98:1 ✓** |
| `#a8adb6` | 6.37:1 ✓ | 4.65:1 ✓ |

This is the finding that reorders the whole change: **the handle is already below
3:1 against plain panel surface, on every tray in the app, and has been the whole
time.** The mask was protecting it in the one place someone had looked at it —
over artwork — while it failed everywhere else. So the handle was never legible
because of the mask; it was legible in spite of being the wrong colour, in one
overlay, by having the background removed.

`#9aa0aa` is chosen over `#8b909a` for headroom on the artwork case (3.98 vs
3.27) and over `#a8adb6` because past that point the handle starts to read as a
lit control rather than an affordance.

**One handle for every tray.** `.sheet__handle` changes once in `overlays.css`.
Scoping a lighter handle to `.modal__fixed` alone was considered and rejected: it
would leave every other tray at 1.75:1, and it makes one component two, which is
the drift `.genre-item` and the shared `.sheet__head`/`.modal__head` rule already
exist to prevent. Two trays are rarely on screen together, so a divergence here
would never be noticed.

**Alternative considered — keep a shorter mask.** Rejected on the request, and it
would not have helped: a shorter fade still fades, and the user is objecting to
the fade itself, not to its length.

### 3. The gap belongs to the body that follows a fixed region

```css
.modal__fixed + .modal__body { padding-top: 20px; }
```

in `overlays.css`, next to `.modal__body`'s own `padding: 0 20px 20px`.

`20px` matches the body's horizontal inset, so the distance below the division is
the same as the distance at its sides — a number with a reason rather than one
that has to be re-guessed.

**Keyed on the DOM, not on the detail overlay.** `.modal__fixed` exists in
exactly one overlay today, so an adjacent-sibling selector is precise now and
stays correct if a second overlay ever pins a region: the rule reads "a scrolling
body that has a pinned region above it", which is the actual condition. Adding a
detail-overlay-specific class would be a registry by another route, which is the
pattern `overlays.js` explicitly refuses.

`+` and not `~`: `.modal__body` is the immediate next sibling of `.modal__fixed`,
and `~` would additionally match any later body, which is not what is meant. (Not
the same situation as the `.sheet__grip ~ …head` rule in the media query, where
`.modal-backdrop-art` sits between the two.)

Overlays with no fixed region — trailer, roulette, genre, server switcher — are
unmatched and keep the spacing they have.

### 4. Pin the numbers in a test, the way `test_pill_contrast.py` does

`make test` has no browser, so what can be pinned is the **source decision**: the
CSS values, and the arithmetic over them.

- `tests/test_overlay_layering.py::test_artwork_clears_past_the_handle_not_up_to_it`
  is replaced by a test that parses `.modal-backdrop-art`'s `opacity`, composites
  white over `--surface` at it, and asserts `--muted-text` clears 4.5:1 — plus an
  assertion that no `mask-image` remains on the rule.
- `tests/test_overlay_markup.py::test_the_backdrop_artwork_does_not_cover_the_grab_handle`
  is replaced by a handle-contrast test asserting `.sheet__handle`'s colour
  clears 3:1 against both `--surface` and that same composite.
- A test asserts `--grip-clear` and `--grip-height` are gone from `tokens.css`
  and referenced nowhere, so the mask cannot come back by half.
- `test_grip_is_lifted_above_the_artwork` is unchanged and must still pass.

The contrast helper is written once and shared rather than copied out of
`test_pill_contrast.py` — two hand-copied sRGB curves drift, and the symptom
would be two tests disagreeing about whether the same pair passes.

## Risks / Trade-offs

- **The artwork at 0.10 is much subtler than at 0.35, and someone may read that
  as it having been removed.** → It is `#3f3f3f` against a `#2a2a2a` panel, a
  clearly visible difference, and it is what the requirement permits: the
  identity block is the content, the artwork is texture. Verified by looking at
  it, on an item with a bright backdrop and on one with a dark one.
- **Lightening the shared handle changes every tray, not just this one.** → That
  is intended and it is an improvement in each: 1.75:1 → 5.46:1 against plain
  surface. The risk is only that it looks brighter than before; check the genre,
  Actions, trailer and roulette trays alongside the detail tray.
- **The contrast tests encode a spec, and a test derived from a spec inherits the
  spec's blind spot** — the repo has already shipped a pill-contrast test that
  passed the build that reached a user. → The arithmetic here is over a
  composited worst case rather than over a resting state, so the failure mode
  that caught the pills (a transitional frame no screenshot shows) does not
  apply. Still verify in a browser on a real bright backdrop rather than trusting
  the number alone.
- **`+ .modal__body` is a positional selector, so reordering the detail overlay's
  markup would silently drop the gap.** → Nothing errors; the heading just goes
  flush again. Accepted: the two elements are a pair by construction — a pinned
  region is only meaningful directly above the body it pins content out of — and
  the alternative is a class that has to be remembered.
- **Someone re-adds the fade later because the handle looks bare on a bright
  backdrop.** → The rule and the reason live in the spec and in a comment at the
  rule, and the deleted tokens mean re-adding the mask requires re-adding them
  too, which the token test blocks.

## Migration Plan

None. Three CSS values, two deleted declarations, two deleted tokens, one added
rule. No data format, no configuration, no container change, so no
`make docker-smoke` and nothing for an existing install to do. Rollback is
reverting the commit.

## Open Questions

- `0.10` is derived from a 4.5:1 bar taken against fully white artwork. If the
  artwork turns out to read as too faint in practice, the honest lever is the
  *text* — lifting the year and metadata off `--muted-text` would let the artwork
  come back up — not quietly relaxing the bar. Decide that after looking at it,
  not before.
