# `tools/` — development only

Nothing here ships. The `Dockerfile` copies `scripts/`, `web/` and `config/`, and
this directory is in none of them. It is also not imported by anything under
`tests/`, so `make test` does not depend on it.

**This directory is temporary.** It exists to get the rewrite finished. See
[pre-release-cleanup.md](../docs/pre-release-cleanup.md) for what happens to it.

| File | What |
| --- | --- |
| `browser.py` | Drive a real Chromium over CDP and measure the rendered page |
| `seed_library.py` | Generate a fake library snapshot at any size |
| `grid_metrics.py` | Measure the media grid's cost — nodes, frame rate, invisible cards |

## Why these are committed rather than written per session

Both had been rebuilt from scratch more than once, from notes in old
transcripts, because neither lived anywhere. That is how a session ends up
verifying the wrong thing.

**`browser.py`** exists because the obvious approach does not work.
`chromium --headless --virtual-time-budget=… --dump-dom` never fires
`requestAnimationFrame`, and Alpine's transitions, the overlay scroll lock and
the focus manager all sequence on it. Every overlay sits frozen at
`overlay-shut overlay-opening`, so the run proves overlays render *shut* and
never opens one. Five bugs reached the user that way while both the suite and
the browser check reported everything fine.

**`seed_library.py`** defaults to **7000 movies** because that is the size at
which the grid used to fail. A 400-item fixture showed nothing wrong, which was
not evidence of health: at 7,000 the page rendered 63,248 nodes, sat at ~3fps
while idle, and left 6,611 cards at `opacity: 0`. **Seed thousands or measure
nothing.**

**`grid_metrics.py`** is the harness that found that and proves it stays fixed.
The grid renders a window near the viewport now, and the bound it guarantees
cannot be checked by `make test` — CI has no browser and no library.
`tests/test_grid_windowing.py` pins the source decisions; this produces the
numbers. Run it at both widths before and after any change to `displayMedia()`:

```bash
python3 tools/grid_metrics.py --label before
```

## Using them

```bash
# 1. A container with a library in it
python tools/seed_library.py --out /tmp/seed --posters 60
docker run -d --name glimpse-dev -p 18081:80 -v /tmp/seed:/app/data \
  -e PLEX_URL=http://127.0.0.1:32400 -e PLEX_TOKEN=x glimpse:dev

# The entrypoint fetches on every start, and a fetch that cannot reach a media
# server DELETES the snapshots. So copy them in after the container is up.
for s in plex jellyfin; do for k in movies tvshows; do
  docker cp /tmp/seed/$s/$k.json glimpse-dev:/app/data/$s/$k.json
done; done
```

```python
# 2. Drive it
from tools.browser import Browser, nginx_requests

browser = Browser()
try:
    browser.viewport(390, 844)  # then repeat at 1280 — they differ
    browser.goto('http://127.0.0.1:18081/')

    since = nginx_requests('glimpse-dev')
    browser.goto('http://127.0.0.1:18081/')
    log = since()
    print('poster requests:', sum(1 for line in log.splitlines() if '/posters/' in line))

    print(browser.measure('.sheet__head'))
finally:
    browser.close()
```

## Two traps these encode

- **Test at 1280px _and_ 390px.** The overlay system behaves differently at each
  by design, so one width proves nothing.
- **Never measure caching with `PerformanceResourceTiming.transferSize`.** It
  reads `0` for anything a service worker handled, cached or not, so a fetched
  resource is indistinguishable from a cached one. It once reported the library
  snapshots as cache hits when every one had been fetched. Use
  `nginx_requests()`, which reads the container's own access log.

Requires `chromium` on `PATH` and `websocket-client` installed.
