## Why

On a phone, scrolling the Movies grid makes every poster on screen blink back to
a loading spinner and fade in again — including posters the viewer has already
scrolled past once, on the way back up. The grid is destroying and rebuilding
every card it holds each time the viewer crosses a single row.

The TV Shows grid does not flicker, and that is worse rather than better: its
windowing never switches on at all, so it renders only its first ~120 shows and
the rest of the library cannot be reached by scrolling. On a phone the tab pills
are hidden, so the swipe is the only way into that tab — and the swipe is the
path that breaks it. There is no route on a phone that reaches TV Shows with a
working grid.

Reported against ~2,000 movies on a Pixel; confirmed by rotating the device,
which repairs the TV Shows grid and makes it start flickering too.

## What Changes

- The rendered window is re-anchored when the viewer approaches its edge, rather
  than every time they cross a row. At two columns the window holds 60 rows and
  currently rebuilds all of it to gain one — roughly a 1.7% change in what is
  rendered for a 100% teardown of what is on screen.
- The window is centred on the viewer instead of being anchored four rows above
  them with fifty-six below. The present asymmetry is why scrolling **up** is the
  worst case: there is almost no pre-rendered runway in that direction.
- A poster that has already loaded is not returned to its loading placeholder
  when its card is rebuilt. Re-rendering becomes invisible instead of becoming a
  flicker.
- Grid geometry is never recorded from a grid that is not laid out. The incoming
  tab is deliberately rendered while hidden — so that no part of it is visible
  before it has content, which is an existing requirement — and it is measured in
  the same breath, against a card whose height is zero.
- A failed measurement stops being storable as a working state. A row pitch of
  zero currently means both "not measured yet" and "windowing disabled", so a tab
  that was never measurable presents as a healthy tab that simply ends early.

This change does not touch the frozen `docker-compose.yml` surface: no
environment variable, port, volume or image name is added, removed or
reinterpreted. It is confined to the grid's rendering in `web/index.html`.

## Capabilities

### New Capabilities

None. Both defects sit inside an existing capability.

### Modified Capabilities

- `media-browsing`: adds a requirement that the grid does not rebuild the cards
  currently on screen in order to extend its window, and a requirement that the
  grid's geometry is only recorded from a laid-out grid with an unmeasured grid
  refusing to render a window rather than rendering a broken one. Also adds a
  scenario to the existing **Every item remains reachable by scrolling**
  requirement covering a tab first shown by the swipe gesture, which is the case
  that currently fails.

## Impact

- `web/index.html` — `measureGrid()`, `renderWindow()`, `desiredFirstIndex()`,
  `updateGridWindow()`, `buildCard()`, `displayMedia()`, and the image
  `IntersectionObserver`.
- `tests/test_grid_windowing.py` — `test_scrolling_inside_the_window_does_nothing`
  asserts a guard whose name describes a guarantee the code has never provided on
  a phone. The assertion changes with the re-anchoring policy it pins.
- `tools/grid_metrics.py` — the behavioural half. Neither defect is reachable by
  `make test`: a zero-height measurement needs a browser, and the flicker needs a
  library large enough to scroll through a window.
- No Python, no `Dockerfile`, no `config/`, no service worker changes, so
  `make docker-smoke` is not implicated.
