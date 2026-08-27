## 1. The panel joins the shared surface

- [x] 1.1 In `web/assets/overlays.css`, remove `background: #000` from
      `.modal__panel--video`, leaving only its width. Update the rule's comment
      to say the modifier now sizes and nothing else.
- [x] 1.2 In `web/index.html`, move black to `.trailer-container` as an opaque
      `background: #000`, replacing `rgba(0, 0, 0, 0.3)`. Comment it as a
      property of the medium — a video letterboxes against its own container —
      not a theme choice.
- [x] 1.3 Change `.trailer-loading`'s background from `rgba(26, 26, 26, 0.7)` to
      the same opaque `#000`, adjacent to 1.2 and commented as a pair: the two
      must stay equal or the well changes colour when the video arrives.
- [x] 1.4 Replace both hardcoded `8px` radii (`.trailer-container` and its
      `iframe`) with `var(--radius-md)`.
- [x] 1.5 Delete `box-shadow` from `.trailer-container iframe` — the container
      clips, so it has never rendered. Keep the iframe's own `border-radius`
      with a note that Safari does not reliably clip an iframe to a rounded
      ancestor.

## 2. The spinner is rebuilt from tokens

- [x] 2.1 Change `.trailer-spinner`'s track from `rgba(229, 160, 13, 0.2)` —
      Plex yellow, wrong on the other two themes — to `var(--border)`. Leave
      `border-top-color: var(--primary-color)`, which is the part that should
      follow the accent.
- [x] 2.2 Point `.trailer-spinner`'s `animation` at the app's existing
      `spinner-rotate` keyframe and delete `@keyframes trailer-spin`, which is a
      byte-identical duplicate.
- [x] 2.3 Verify no other rule referenced `trailer-spin`
      (`grep -rn "trailer-spin" web/`).

## 3. The head names the item

- [x] 3.1 Give the trailer's `<h2>` `id="trailer-title"`, keeping `Trailer` as
      its authored text so the overlay is labelled before its first open.
- [x] 3.2 In `openTrailer(title, year)`, set that heading to `Title (Year)`, or
      to `Title` alone when `year` is missing.
- [x] 3.3 In the same place, set the panel's `aria-label` to
      `Trailer: Title (Year)`, so a screen reader hears the kind of overlay and
      the item while the visible head shows only the item.
- [x] 3.4 In `closeTrailer()`, reset the heading text and the `aria-label` inside
      the existing guarded timeout, alongside the loading-state reset, so the
      next open cannot show the previous item's name.
- [x] 3.5 Add `min-width: 0` plus a **one-line clamp** to a shared
      `.sheet__title, .modal__head h2` rule in `overlays.css`. **Set no
      `line-height`** — the shared-head comment records that the title's
      half-leading is half the gap below the grab handle. Note in the comment
      that `min-width: 0` is load-bearing: a flex item's default
      `min-width: auto` would push the close button out of the panel instead of
      truncating.
      **Done with a clamp, not the `white-space: nowrap` this task originally
      specified.** Implementing it surfaced the conflict: the detail overlay's
      title is data too and is deliberately allowed three lines by
      `.modal__fixed .modal-title` in `index.html`, which is (0,2,0) to this
      rule's (0,1,1). Nowrap sets a property that rule does not declare, so it
      would have won everywhere and silently flattened that title to one line. A
      clamp composes — the shared rule states the default, an overlay with the
      room states its own. `design.md` decision 4 was updated to match.

## 4. Tray on touch

- [x] 4.1 Add `modal--tray-on-touch` to the trailer overlay's root element.
- [x] 4.2 Add the grip region as the panel's first child:
      `<div class="sheet__grip"><span class="sheet__handle"></span></div>`.
      Comment it the way the roulette's is: the modifier hides the × on touch,
      so the modifier and the handle arrive together or not at all.
- [x] 4.3 Wrap `.trailer-container` in a `<div class="modal__body">` so the panel
      has three regions and the video takes the same inset as every other
      overlay's content. Keep the head a **sibling** of the body, never an
      ancestor — the drag gesture's `touch-action: none` is honoured only while
      the head is not the scroller.
- [x] 4.4 Rewrite the overlay's markup comment: it currently states the trailer
      is a dialog at every width and gives the reason. Replace it with why that
      reasoning described a desktop — at touch widths a tray *is* the screen's
      width and a full-width 16:9 video fills it exactly.
- [x] 4.5 Correct the two stale comments in `overlays.css`: the file header
      ("the trailer is a dialog everywhere") and the `.sheet__grip ~ …head` rule
      ("The trailer has no grip at any width and is deliberately untouched").
      The trailer now takes that padding compensation, and should.
- [x] 4.6 Update the touch block's comment above `.modal--tray-on-touch`, which
      names the trailer as an overlay that stays centred.

## 5. The well is capped by height

- [x] 5.1 Replace `.trailer-container`'s `padding-bottom: 56.25%` / `height: 0`
      ratio hack with `aspect-ratio: 16 / 9`.
- [x] 5.2 Cap it with `width: min(100%, calc((88vh - 120px) * 16 / 9))` and
      `margin-inline: auto`. Comment why the **width** is capped and not the
      height: `max-height` on an aspect-ratio box clamps the height while the
      width keeps filling its container, which breaks the ratio and letterboxes
      the video inside its own well. Record where `88vh` and `120px` come from —
      the panel's own `max-height`, and the worst-case chrome above and below it.

## 6. The error state stops destroying the spinner

- [x] 6.1 Add a hidden error line inside `.trailer-loading` alongside the spinner
      and the status text, with its colour in the stylesheet rather than in an
      inline `style` attribute.
- [x] 6.2 Change `iframe.onerror` to toggle between the loading and error lines
      instead of replacing `.trailer-loading`'s `innerHTML`.
- [x] 6.3 Delete the loading-markup rebuild string from `closeTrailer()` and
      reset by toggling instead — that string was a second copy of markup also
      authored in the HTML, with nothing to catch the two drifting apart.

## 7. Tests

- [x] 7.1 In `tests/test_tray_presentation.py`, assert the trailer overlay root
      carries `modal--tray-on-touch` (mirroring
      `test_roulette_is_a_tray_on_touch`).
- [x] 7.2 Assert the trailer panel declares no background of its own — that
      `.modal__panel--video`'s block contains no `background`. This is the
      regression that started this change.
- [x] 7.3 Assert the well and its loading state declare the **same** background
      value, so the pair cannot drift into a visible colour change at load.
- [x] 7.4 Assert `.trailer-spinner` contains no literal `rgba(`/hex colour — its
      track and leading edge must both come from tokens.
- [x] 7.5 Assert `@keyframes trailer-spin` is gone and `.trailer-spinner`
      animates `spinner-rotate`.
- [x] 7.6 Assert the regions are in order — grip, then head, then body — for
      **every** panel that has a grip, not just the trailer's.
      **Written in `tests/test_tray_presentation.py`, not
      `test_overlay_markup.py` as this task said:** the DOM-walking
      `overlay_panels()` helper that yields a panel's full markup lives there,
      and duplicating it into the other file to honour the task's filename would
      have been the worse trade.
- [x] 7.7 Assert the shared head-title rule sets no `line-height`, guarding the
      truncation added in 3.5 from acquiring one later.
      **No new test needed — already covered.**
      `test_no_overlay_title_sets_its_own_line_height` walks every rule in both
      files and matches `.sheet__title` and `.modal__head h2` by name, so the new
      shared rule is in its scope already. Verified by reading it rather than
      assumed.
- [x] 7.8 Run `make lint` and `make test`; run `make fmt` if formatting is
      flagged. No `make docker-smoke` — nothing under `Dockerfile`, `config/` or
      `scripts/` is touched.

## 8. Browser verification

`make test` has no browser, so none of the following is covered by it. Check all
three server themes (`data-server` = `plex`, `jellyfin`, `emby`) where colour is
involved.

- [ ] 8.1 Desktop, ~1920×1080: the panel's head, border and radius are
      indistinguishable from the roulette overlay's opened beside it. The × is
      shown, the grab handle is not.
- [ ] 8.2 Desktop: the well is one colour through the whole load — watch the
      moment the iframe fades in and confirm nothing shifts behind it.
- [ ] 8.3 Desktop: the head shows the film's title and year, and a very long
      title ellipses without pushing the × out of the panel or growing the head.
- [ ] 8.4 Desktop, short viewport ~1440×700: the height cap binds — the well
      stays 16:9 and the panel does not scroll.
- [ ] 8.5 Phone, portrait: the overlay docks to the bottom edge and slides up,
      the grab handle is shown, the × is not.
- [ ] 8.6 Phone: drag the handle down — the trailer dismisses **and the audio
      stops**. Use a real touch target or device emulation with touch input; a
      narrow desktop window shows the tray shape but dispatches no touch events,
      so the handle will look right and drag nothing.
- [ ] 8.7 Phone, landscape ~667×375: the video fits inside the tray without
      overflowing it. This is the case the height cap exists for.
- [ ] 8.8 Open the trailer from the detail overlay, dismiss it, and confirm the
      detail overlay is still open beneath and keyboard focus returns to the
      Watch Trailer button.
- [ ] 8.9 Open a trailer, dismiss it, then open a different film's — the head
      shows the new title, never the previous one.
- [ ] 8.10 Confirm the four constant-titled overlays (roulette, genre, server
      switcher, menu) still show their full titles after the shared truncation
      rule in 3.5.

## 9. Documentation

- [x] 9.1 Check whether `README.md`, `docs/` or `CLAUDE.md` describe the trailer
      as a dialog at every width, and correct them in the same commit. If
      nothing user-facing changed, say so explicitly in the PR rather than
      inventing edits.
- [x] 9.2 Consider whether `CLAUDE.md`'s overlay section should record the
      "an overlay's panel never declares its own background" rule and the
      width-not-height aspect-ratio cap, both of which are the kind of decision
      that gets undone by someone tidying up.
