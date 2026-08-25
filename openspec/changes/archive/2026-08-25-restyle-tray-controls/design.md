## Context

Four presentation defects left over from the tray conversion, plus one rule the
conversion applied to dialogs and not to trays.

Measured against a container built from `dev`, driven over CDP:

| Observed | Cause |
| --- | --- |
| Genre entries render as white system buttons, wrapping raggedly | `.genre-item` became a `<button>`; its rule still describes `<div>` rows |
| `Action23`, `All Genres813` | `.genre-item__label` and `.genre-item__count` have **no rules at all** |
| Server switcher looks identical | `populateServerTray()` reuses `.genre-item` |
| A hairline crosses the detail artwork | `.modal__head { border-bottom }` applies inside `.modal__fixed` |
| Roulette centred on a phone | no `.modal--tray-on-touch`, and no regions to support it |
| Genre tray shows a handle *and* a × on touch | the rule hiding the × is scoped to `.modal--tray-on-touch` |

The through-line is the conversion changing an element's *kind* without its
styling following. `.genre-item` was a row in a dropdown; it is now a button in a
tray. The old rule — `padding`, `cursor`, `white-space`, `font-size` — is not
wrong so much as no longer about anything: it never described a background, a
border or a display mode, because a `<div>` in a list needed none of those.

## Goals / Non-Goals

**Goals:**

- The genre and server trays look designed rather than defaulted.
- One dismissal affordance per overlay per width, always at least one.
- The roulette is a tray on touch, structurally, not by class alone.
- No divider drawn across artwork.
- Tests that fail if the roulette loses a region or an overlay loses its only
  way to close.

**Non-Goals:**

- Any behavior change. Every control does what it already does.
- Reintroducing a desktop dropdown for genre or server. One overlay at both
  widths is the decision the rewrite made, and two implementations of one control
  is what it deleted.
- Changing tray motion, layering, or bindings — that is the sibling change.
- A design-token overhaul. These rules consume existing tokens.

## Decisions

### 1. `.genre-item` becomes a pill, and the count becomes a badge

Marquee's `.choice span` is the closest existing precedent: an elevated fill so
an unselected option reads as a control rather than blending into the surface
behind it, a pill radius, a border, and a checked state mixed from the accent.
Glimpse has `--surface-2` for exactly the "control sitting on a surface" tier,
and the tray body is `--surface`, so the tier is already there to use.

**Alternative considered:** full-width rows, one genre per line. Rejected — there
are 35 genres and a phone tray is 88vh; the list would be a scroll of nearly
identical bars, and the count would sit far from the name it qualifies. Wrapping
pills show roughly four per row and let the eye scan alphabetically.

**Alternative considered:** a `<select>`. Rejected — it discards the counts, which
are the reason to open the tray at all.

The count is a separate element already in the markup, so this is styling, not
restructuring. It gets a quieter colour and its own spacing. Its element is
absent when there is nothing to show, which is already what `genreItem()` does —
it writes an empty string — so the rule must not reserve space for an empty
badge.

### 2. The head divider is scoped, not deleted

`.modal__head { border-bottom }` is right on the trailer, the roulette and the
server switcher, whose heads sit on flat surface. It is wrong only inside
`.modal__fixed`, where the head is painted over the item's artwork.

So the removal is scoped to `.modal__fixed .modal__head` rather than taken off
the base rule. The base rule is doing its job everywhere else, and removing it
globally would flatten three overlays to fix one.

`.modal-header`'s own `border-bottom` stays. It marks where the fixed region ends
and the scrolling region begins — real structure, at the foot of the identity
block, on surface. Removing both would leave the summary sliding under the poster
with nothing to say where one stopped.

### 3. The roulette gains three regions, not a modifier

`.modal--tray-on-touch` alone would produce a tray that cannot be dismissed:
the modifier hides `.overlay__close` on touch, the overlay has no grab handle to
replace it with, and backdrop dismissal is deliberately suppressed while it is
choosing. So the modifier comes with `.sheet__grip`, `.modal__head` and
`.modal__body`.

That is not scope creep — it is the overlay system's contract. The drag gesture
finds its subjects by class in the DOM, the scroll lock and focus manager key on
the panel's attributes, and a panel without the regions is simply not an overlay
this system can drive.

It also closes a real gap: **the roulette has no close control at all while it is
choosing**, at any width. That was defensible when the overlay was a
two-second status flash, and stops being defensible the moment a pick hangs.
Giving it a head gives it somewhere to put one.

Backdrop dismissal stays suppressed. The existing reasoning holds — a stray tap
cancelling a pick the user just asked for reads as a broken button — and it is
why the handle and the × have to be explicit.

### 4. Hiding a tray's × is a one-line move of an existing rule

`.modal--tray-on-touch .overlay__close { display: none }` already exists in the
touch block of `overlays.css`, with a comment giving the reason. A `.sheet` below
768px is a tray by definition, so the same reason applies and the selector simply
grows.

The reciprocal already holds: above 768px `.sheet__grip` is hidden and the × is
shown. So no width ends with neither — but that is worth a test rather than an
assumption, because it is exactly the pair that drifted apart at 992px and 768px
once before.

## Risks / Trade-offs

- **Pills at a narrow width could overflow.** A long genre name — "Science
  Fiction", "Martial Arts" — in a 390px tray. → The row wraps and an entry may
  take a whole line; that is acceptable. Verify at 320px, the narrowest phone
  worth supporting.

- **The roulette's markup change touches `test_overlay_markup.py`'s subjects.**
  It asserts every panel carries `role`, `aria-modal` and `tabindex`. → The panel
  already has all three; adding a head does not remove them. Run the suite.

- **Focus management on the roulette's new close control.** The overlay is
  `aria-live="polite"` and moves focus to the panel on open. → A close button
  inside the head is an ordinary focusable child; the existing trap handles it.
  Worth checking that the live region still announces after the head is added.

- **Restyling a shared class changes two trays at once.** That is the intent, and
  it is also how an unintended change reaches somewhere unlooked-at. → The only
  two users of `.genre-item` are the genre tray and the server tray; grep to
  confirm before and after.

- **This is the last change before `:dev` validation.** Three other changes are
  waiting on it. → Keep it to presentation; resist folding in anything behavioral
  that turns up.

## Open Questions

- Should the genre tray's entries be sorted with the active one first, so the
  current filter is visible without scanning? Out of scope here — it changes what
  the list *is*, not how it looks — but worth asking once it is legible.
- The `.genre-item` name is now doing double duty for servers. Rename to
  something neutral (`.tray-choice`?) in a later pass, or leave it? Leaning
  leave: a rename touches two JS builders and every rule, for no user-visible
  gain, and this change should stay small.
