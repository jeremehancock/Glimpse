## Context

The trailer overlay predates the shared overlay system. When the six bespoke
overlays were converted to `.sheet` / `.modal`, the trailer's *shell* was
converted but its interior was not: it still carries its own inline `<style>`
block with hardcoded colours, its own spinner component with its own keyframes,
and a panel that overrides the shared surface with `background: #000`.

Three things follow from that, and all three are visible in the screenshot that
prompted this change:

1. `.modal__panel--video` sets `background: #000`, so the head is pure black
   while every other overlay's head is `--surface` (`#2a2a2a`).
2. `.trailer-loading` sets `background-color: rgba(26, 26, 26, 0.7)`. Over the
   black container that composites to **`#121212`** — so the loading area and the
   head are two different blacks, side by side, with a visible seam between them.
   When the video arrives the region jumps from `#121212` to `#000`.
3. `.trailer-spinner` hardcodes `rgba(229, 160, 13, 0.2)` for its track — Plex
   yellow at 20%. On Jellyfin (`#00a4dc`) and Emby (`#52c41a`) the ring is drawn
   in a colour from a different server's theme, and nothing says so.

Separately, the head reads `Trailer` for every item, and the overlay is the only
one in the app still centred on a phone. The user has chosen the tray shape for
touch.

Constraints this design works inside:

- No build step. `web/` is served as authored, so this is HTML + CSS + a small
  amount of vanilla JS in the existing inline blocks.
- The overlay system is DOM-keyed, not registry-keyed. Correct markup is the
  whole requirement — nothing has to be registered for the drag, the scroll lock
  or the focus manager to pick the trailer up.
- `openTrailer(title, year)` already receives everything the head needs. No new
  data path, no second read of anything.
- The frozen `docker-compose.yml` surface is untouched.

## Goals / Non-Goals

**Goals:**

- The trailer panel is indistinguishable from every other overlay's panel.
- The region holding the video is one colour, before and after the video loads.
- The head names the item, and says so to a screen reader.
- The overlay is a tray on touch with the affordances and regions the tray shape
  requires, and its video cannot overflow a short viewport.
- The trailer's inline CSS stops carrying values that duplicate or contradict
  tokens.

**Non-Goals:**

- Changing the embed, its provider, its URL, or the autoplay behaviour.
- Changing when playback stops, or the detail-overlay interaction around it.
- Touching the roulette's spinner, or any other overlay's interior.
- Making the trailer available for TV shows. It is movies-only today and stays
  that way.
- Any Docker, nginx, entrypoint, or Python change.

## Decisions

### 1. The panel loses its background override; only the well is black

`.modal__panel--video` keeps `width: min(960px, 100%)` and drops
`background: #000`. The base `.modal__panel` then supplies `--surface`,
`--border`, `--radius-lg` and `--elev-4`, exactly as it does for the roulette and
the detail overlay.

Black moves to `.trailer-container` — the well the video sits in — and stays
there. That black is not a theme choice: a 16:9 embed letterboxes against its own
container whenever the source is not exactly 16:9, and letterboxing against
`#2a2a2a` reads as a rendering fault rather than as a frame. It is a property of
the medium, so it is scoped to the medium.

*Alternative considered — make the whole panel black, which is the other option
the user offered.* Rejected: it would make the trailer the only overlay in the
app that does not use the surface token, which is the same divergence this change
exists to remove, just tidied up. It would also mean a per-server theme that
stops at this one overlay's border.

### 2. The loading state is opaque and the same black as the well

`.trailer-loading` becomes `background: #000` rather than a translucent light
wash. The well is then one colour whether it is holding a spinner or a video, so
the moment the iframe fades in — the moment the viewer is looking hardest — the
panel does not change colour underneath it.

Both blacks are written as the same value in the same style block, adjacent, with
a comment saying they are a pair. There is no token for them: `--surface` and
friends describe the app's chrome, and a "video black" token with one reader
would be a shared name for a local decision.

### 3. The head shows the item; the accessible name says it is a trailer

The `<h2>` gets `id="trailer-title"` and its text is set by `openTrailer()` to
`Title (Year)`, or just `Title` when there is no year. The authored markup keeps
`Trailer` as its text so the overlay is never unlabelled before the first open.

The panel keeps `aria-label`, and `openTrailer()` rewrites it to
`Trailer: Title (Year)`. A screen reader then announces both the kind of overlay
and the item; a sighted viewer sees only the item, because prefixing the visible
head with `Trailer: ` would spend the front of a truncated line on a word the
head already implies.

*Alternative considered — `aria-labelledby` pointing at the h2, plus a
visually-hidden "Trailer" span inside it.* Rejected: it needs a new
visually-hidden utility class the app does not have, for one label, and it makes
the accessible name depend on markup that is easy to reorder. Setting the
attribute in the same function that sets the title keeps the two impossible to
get out of step.

`closeTrailer()` resets both, inside the same guarded timeout that already
restores the loading state, so nothing can show the previous item's name for a
frame on the next open.

### 4. Truncation goes on the shared head rule, not on the trailer

`.sheet__title, .modal__head h2` gets `min-width: 0` plus a one-line clamp
(`display: -webkit-box; -webkit-box-orient: vertical; line-clamp: 1; overflow:
hidden`). The `min-width: 0` is required — the title is a flex child, and a flex
item's default `min-width: auto` refuses to shrink below its content, so without
it the title pushes the close button out of the panel instead of truncating.

**A clamp and not `white-space: nowrap`, and this was found during
implementation rather than here.** The detail overlay's title is data too, and
`.modal__fixed .modal-title` in `index.html` deliberately allows it three lines.
That rule is (0,2,0) to this one's (0,1,1), so it wins on the clamp — but it
declares no `white-space`, so nowrap would have won everywhere and silently
flattened the detail overlay's title to a single line. Nothing would have failed;
it would simply have started truncating a title it had always wrapped.

A clamp composes where nowrap collides: the shared rule states the default bound,
and an overlay with the room to spare states its own. It is also the app's
existing idiom — three other rules here clamp by line count — and
`-webkit-box` is already proven inside a `.modal__head` by that very rule.

It goes on the shared rule because the two heads are deliberately one rule, and
because the trailer is simply the first head in the app whose title is *data* —
every other one is a constant short enough that this changes nothing for them
today. Scoping it to the trailer would leave the next data-driven head to
rediscover the same problem.

Critically it sets **no `line-height`**. The shared-head comment records that the
title's half-leading is half the gap below the grab handle, and that an override
here is the edit most likely to undo that silently. `white-space: nowrap` bounds
the head's height without touching type metrics.

*Why the head must be bounded at all:* on touch the head is part of the drag
region (`touch-action: none`, and it is one of the four selectors the gesture
matches). A head that grows with its title is a drag region whose height depends
on which film was opened.

### 5. Tray on touch, with the regions the modifier requires

The overlay root gains `modal--tray-on-touch`, and the panel gains the three
regions: a `.sheet__grip` holding a `.sheet__handle`, the existing
`.modal__head`, and a new `.modal__body` wrapping the well.

The modifier and the regions arrive together, without exception. The modifier
hides the × below 768px; a panel carrying the modifier and no grab handle is an
overlay whose only remaining dismissals are the backdrop and Escape, neither of
which is visible. This is the failure the roulette's markup comment already
records.

Everything else follows from existing rules with no new CSS:

| Behaviour | Supplied by |
| --- | --- |
| Docked, full width, slide-up, tray radius and shadow below 768px | `.modal--tray-on-touch` block in `overlays.css` |
| Handle shown below 768px, hidden above | `.modal .sheet__grip` + the touch block |
| × hidden below 768px, shown above | the same pair |
| Drag-to-dismiss on grip and head | the gesture's selector list — it finds them in the DOM |
| Head padding compensation at ≥768px where the handle is hidden | `.sheet__grip ~ .modal__head` |

That last one is a behaviour change the trailer picks up for free and should:
the rule exists precisely for a panel that has a grip in the markup and has it
hidden, which the trailer now is. The `overlays.css` comment that names the
trailer as permanently exempt from it becomes wrong and is corrected in the same
commit.

Wrapping the well in `.modal__body` is what makes the panel three regions rather
than two, and it also gives the video the same 20px inset every other overlay's
content has. The body is the designated scroller, which is fine — with the height
cap below it never has anything to scroll.

### 6. The well is capped by height, not only by width

The `padding-bottom: 56.25%` ratio hack is replaced by `aspect-ratio: 16 / 9`,
and the well's **width** is capped by the height available:

```css
width: min(100%, calc((88vh - 120px) * 16 / 9));
aspect-ratio: 16 / 9;
margin-inline: auto;
```

Capping the width rather than the height is the part that matters. `max-height`
on an `aspect-ratio` box clamps the height while the width goes on filling its
container, which silently breaks the ratio and letterboxes the video *inside* its
own well. Deriving the width from the height budget keeps the box 16:9 at every
size.

`88vh` is the panel's own `max-height`; `120px` is the panel chrome above and
below the well, rounded up from the worst case (grip 17px + head 74px + body
padding 20px = 111px on touch; 98px on a pointer, where the grip is hidden but
the head takes the 18px compensation). Worked through:

| Viewport | Shape | Well | Panel total vs. 88vh |
| --- | --- | --- | --- |
| 390 × 844 phone | tray | 350 × 197 | 308 ≤ 743 |
| 667 × 375 phone landscape | tray | 373 × 210 | 321 ≤ 330 |
| 1440 × 700 short desktop | dialog | 882 × 496 | 594 ≤ 616 |
| 1920 × 1080 desktop | dialog | 918 × 516 | 614 ≤ 950 |

The cap binds only on short viewports, which is the intent. On a normal desktop
the 960px panel is the narrower constraint and the calc never applies.

### 7. The spinner is rebuilt from tokens and stops duplicating a keyframe

- Track: `var(--border)` instead of Plex yellow at 20%. It is a decorative ring,
  it is legible on black, and it is a token, so it cannot drift per server.
- Leading edge: `var(--primary-color)`, unchanged — this is the one part that
  *should* follow the server accent, and it already does.
- Animation: the app already declares `@keyframes spinner-rotate` for
  `.loading-spinner`. `@keyframes trailer-spin` is a byte-identical second copy
  and is deleted.

*Alternative considered — `color-mix(in srgb, var(--primary-color) 25%,
transparent)` for the track.* It is the more faithful translation of the original
intent, but it adds a CSS feature with a later support floor than anything else
in the file, for a decorative ring on which nothing depends.

*Alternative considered — merging `.trailer-spinner` into `.loading-spinner`.*
Rejected: `.loading-spinner`'s track is `rgba(0, 0, 0, 0.1)`, chosen for the
poster placeholder's light `--tab-bg` surface, and it would be invisible on
black. Two spinners that legitimately sit on opposite surfaces are not one
component. Only the duplicated *keyframe* is merged.

### 8. The error state gets its own element, so the loading markup exists once

Today `iframe.onerror` replaces `.trailer-loading`'s `innerHTML`, which destroys
the spinner — so `closeTrailer()` has to rebuild it from a string. That string is
a second copy of markup that is also authored in the HTML, and the two can drift
with nothing to catch it.

Instead, `.trailer-loading` holds a spinner, a status line, and a hidden error
line. The error path toggles which is shown; nothing is ever destroyed, so
`closeTrailer()` resets by toggling back rather than by re-emitting HTML. The
error colour moves out of the inline `style="color: #ff4444"` into the stylesheet
with the rest of the block.

### 9. Dead declarations are removed rather than left

`.trailer-container iframe` sets `box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5)`
inside a container with `overflow: hidden`. The shadow is clipped away on every
side and has never rendered. It goes — a declaration that appears to do something
and does not is where the next live one hides.

The iframe *keeps* its own `border-radius`, matched to the well's, even though
the well clips. Safari does not reliably clip an iframe to a rounded ancestor,
and the two values are set adjacent to each other with a note.

Hardcoded `8px` radii become `var(--radius-md)`.

## Risks / Trade-offs

- **The × disappears on a phone, and someone will read that as a regression.** →
  It is the app-wide rule (`A tray offers one way to close on touch`), the grab
  handle replaces it, and drag-to-dismiss routes through the backdrop's click
  handler — which is `closeTrailer()`, so a dragged-away trailer stops playing
  exactly like a dismissed one. Verify the drag on a real touch target, not just
  a narrow desktop window: a desktop viewport under 768px shows the tray shape
  but dispatches no touch events, so the handle looks right and drags nothing.

- **`aspect-ratio` replaces a ratio hack that worked everywhere.** → Support is
  universal in browsers that also support the custom properties, `inset` and
  `line-clamp` this app already depends on. Nothing new is required of a client.

- **The head-truncation rule is shared, so it lands on five overlays at once.** →
  It changes nothing visible for the four with constant titles; they are all far
  shorter than their heads. Confirm each still shows its full title.

- **A short landscape phone is the case the height cap exists for and the one
  least likely to be checked.** → It is in the verification list explicitly, at
  667 × 375, where the cap binds hardest.

- **`make test` cannot see any of this.** → It has no browser. The tests pin the
  *source decisions* — the panel declaring no background, the modifier and the
  grip arriving together, the removed keyframe. The appearance has to be checked
  in a browser, on both shapes, on all three server themes.

## Migration Plan

Not applicable in the usual sense: this is presentation-only, in files nginx
serves as authored. There is no data migration, no config change, and no
persisted state involved.

The one deployment note is the caching rule already recorded for this repo —
`/assets/` is network-first at all three layers precisely so a CSS change reaches
an existing client on its next load. `index.html` is not cached. Nothing extra is
needed here; it is worth knowing only so that "the fix isn't showing up" is not
misdiagnosed.

Rollback is reverting the commit.

## Open Questions

None. The one fork — tray versus centred dialog on a phone — was put to the user
and answered: tray on touch.
