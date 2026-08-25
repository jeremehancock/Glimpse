## Why

On a phone the Actions tray opens completely empty — no sort, no genre filter, no
server switcher, no install prompt. The tray animates in, shows its title, and
offers nothing. Between 769px and 992px the same controls are missing from the
page entirely, with no tray to fall back to, so a tablet user cannot sort or
filter the library at all.

The detail tray works, but two things about it read as unfinished: the item's
backdrop artwork runs under the grab handle, so the one affordance that dismisses
the tray sits on top of a picture; and scrolling the overview carries the poster,
year and rating away with it, so the user loses sight of what they are reading
about.

## What Changes

- The Actions tray fills. Sort, genre, server switch and install are reachable on
  a phone again.
- The 769–992px band gets those controls back. The header keeps them until the
  hamburger takes over, so there is no width at which both are hidden.
- The detail overlay's artwork fades out beneath the grab handle instead of
  running to the panel's top edge, and it stops where the item's identity block
  stops rather than at a fixed height that bleeds into the scrolling content.
- The detail overlay gains an explicit **pinned region**: the poster, year,
  content rating, duration and trailer control stay put while the overview,
  genres, cast and date added scroll beneath them. This applies at every width —
  on a phone and on a desktop alike.
- A downward drag on that pinned region dismisses the tray, the same as a drag on
  the handle or the title bar.

Not a breaking change, and it does not touch the frozen `docker-compose.yml`
surface: no environment variable is added, removed or reinterpreted, and an
existing user's compose file runs this unchanged.

## Capabilities

### New Capabilities

None. Both affected capabilities already exist in the map.

### Modified Capabilities

- `media-detail`: adds requirements for which parts of the detail overlay stay
  fixed and which scroll, and for how far the item's backdrop artwork extends.
  Neither is specified today.
- `visual-design`: adds a requirement that a control shown at one width and
  relocated into an overlay at another must be reachable at every width in
  between — the rule the 769–992px gap breaks — and extends the tray drag region
  to cover a pinned identity block.

## Impact

- `web/index.html` — the `.sort-toggle` hide rule and its breakpoint; the
  `.modal-header` element moves out of `.modal__body`; `.modal-backdrop-art`
  sizing; removal of dead `.modal-body` rules and a `margin-top` that no longer
  has anything to clear.
- `web/assets/overlays.css` — the pinned region's presentation, shared by the
  tray and dialog shapes.
- `web/assets/overlays.js` — the drag gesture's opt-in selector list.
- `tests/test_overlay_markup.py` — new regression tests; the existing
  drag-region assertions must keep passing against the new structure.

No Python, no fetchers, no container configuration. `make docker-smoke` is not
required — nothing under `Dockerfile`, `config/` or the entrypoint changes.
