## Why

The trailer overlay is the one overlay in the app that does not look like the
app. It is the only panel painted pure black rather than the shared surface
colour, and while the video loads that black is covered by a lighter grey wash —
so the first thing a viewer sees is a panel whose title bar and body are visibly
two different colours, neither of which matches anything else on screen.

It also does not say what it is about to play. The head reads `Trailer` for every
item, so a viewer who opened it from the detail overlay, or who left it loading
and came back, has nothing on screen naming the film.

And on a phone it is the only overlay still presented as a centred dialog. Every
other overlay docks to the bottom edge with a grab handle in thumb reach; the
trailer floats mid-screen and its only dismissal is a × in the corner furthest
from a thumb.

## What Changes

- **The trailer panel is drawn from the shared token set** — the same surface,
  border, radius and elevation as every other overlay — instead of a hardcoded
  `#000` with a separately hardcoded loading wash over it.
- **The video well stays black**, deliberately and by itself. A video letterboxes
  against its own container, and letterboxing against anything but black reads as
  a rendering fault. The well is black; the *panel* around it is not.
- **The loading state is drawn on that same black well**, so the panel does not
  change colour when the video arrives. Today it is a translucent light wash that
  composites to a different grey than the frame it is standing in for.
- **The head names the item.** The overlay title becomes the item's title and
  year rather than the constant word `Trailer`, and the panel is labelled by that
  heading so a screen reader announces the item too. A long title is clamped so
  it cannot grow the head.
- **On touch the overlay becomes a tray**, with the grab handle and the region
  structure the tray shape requires. The video is capped by height as well as
  width so a short landscape viewport cannot push it past the panel.
- The trailer's spinner stops being a bespoke component with its own hardcoded
  accent and border colours.

No behavioural change to what is played, where the embed comes from, or when
playback stops. **This change does not touch the frozen docker-compose surface**
— no environment variable, port, volume or image name is involved. Nothing under
`scripts/`, `config/` or the `Dockerfile` changes, so no `make docker-smoke` run
is required.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `trailers`: the overlay is a tray on touch rather than a dialog at every width;
  its head names the item being played; the loading indication is presented on
  the same surface as the video it stands in for.
- `visual-design`: the "trailer is a dialog at every width" exception is removed
  — the trailer joins the overlays that are a tray on touch and a dialog on a
  pointer device. A new requirement states that an overlay holding media is drawn
  from the shared surface tokens and only the media well itself is black.

## Impact

- `web/index.html` — the trailer overlay's markup (grip, head, regions,
  `modal--tray-on-touch`, the item-named heading), its inline `<style>` block,
  and `openTrailer()` / `closeTrailer()`, which set and reset the head's text
  alongside the loading state they already manage.
- `web/assets/overlays.css` — `.modal__panel--video` stops overriding the panel
  background; the comment at the top of the file and the one above the touch
  block both name the trailer as a permanent exception and go stale with this
  change.
- `openspec/specs/trailers/spec.md`, `openspec/specs/visual-design/spec.md` —
  both currently state the centred-at-every-width rule.
- `tests/test_tray_presentation.py`, `tests/test_overlay_markup.py` — the trailer
  gains a grab handle and the tray modifier, which these assert about.
- No Python, no fetchers, no snapshot format, no Docker surface.
