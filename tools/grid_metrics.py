"""Measure the media grid's cost against a real library, in a real browser.

Development tooling. Not shipped — the `Dockerfile` copies `scripts/`, `web/`
and `config/`, and this directory is in none of them.

WHY A SCRIPT RATHER THAN A SESSION'S NOTES. Punch-list item 2 was reported,
investigated and left unreproduced twice, because "the trays are choppy" is not
a number. The numbers that matter are node count, idle frame interval, the
forced-layout cost of the scroll lock, and how many cards are still invisible —
and they only mean anything measured the same way before and after a change.

    python3 tools/grid_metrics.py --url http://127.0.0.1:18091/ --label before

Run it at BOTH widths. The grid's column count comes from `auto-fill`, so one
width proves nothing.

Requires `chromium` on PATH, `websocket-client`, and a container seeded by
`tools/seed_library.py` — a few-hundred-item fixture cannot fail these
measurements, which is how this defect survived a browser check once already.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.browser import Browser

# rAF is armed inside an IIFE so re-running it in the same context does not
# throw on a `const` redeclaration — the second call otherwise fails with a bare
# "Uncaught" that looks like the page broke.
ARM_FRAMES = """
(() => {
  window.__gm = {frames: [], run: true};
  const tick = t => {
    window.__gm.frames.push(+t.toFixed(1));
    if (window.__gm.run) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return 'armed';
})()
"""

READ_FRAMES = """
window.__gm.run = false;
(() => {
  const f = window.__gm.frames, d = [];
  for (let i = 1; i < f.length; i++) d.push(+(f[i] - f[i - 1]).toFixed(1));
  return d;
})()
"""

SNAPSHOT = """
(() => {
  const items = Array.from(document.querySelectorAll('.media-item'));
  const invisible = items.filter(e => parseFloat(getComputedStyle(e).opacity) < 0.99);
  const delays = items.map(e => parseFloat(getComputedStyle(e).transitionDelay) || 0);
  const card = items[0] ? items[0].getBoundingClientRect() : null;
  let onScreen = 0;
  for (const el of items) {
    const b = el.getBoundingClientRect();
    if (b.bottom > 0 && b.top < innerHeight) onScreen++;
  }
  return {
    domNodes: document.getElementsByTagName('*').length,
    rendered: items.length,
    onScreen: onScreen,
    scrollHeight: document.documentElement.scrollHeight,
    stillTransparent: invisible.length,
    maxDelaySeconds: delays.length ? +Math.max(...delays).toFixed(2) : 0,
    cardSize: card ? [+card.width.toFixed(1), +card.height.toFixed(1)] : null,
  };
})()
"""

# The scroll lock, applied and released exactly as overlays.js does it, with the
# layout it invalidates forced synchronously so the cost is attributable.
LOCK_COST = """
(() => {
  const root = document.documentElement, body = document.body;
  const t0 = performance.now();
  body.style.top = '-0px';
  root.classList.add('is-overlay-open');
  void body.offsetHeight;
  const apply = performance.now() - t0;
  const t1 = performance.now();
  root.classList.remove('is-overlay-open');
  body.style.top = '';
  void body.offsetHeight;
  return {apply: +apply.toFixed(1), release: +(performance.now() - t1).toFixed(1)};
})()
"""


def frame_stats(browser: Browser, seconds: float = 1.6) -> dict:
    browser.evaluate(ARM_FRAMES, await_promise=False)
    time.sleep(seconds)
    deltas = browser.evaluate(READ_FRAMES, await_promise=False)
    if not deltas:
        return {'frames': 0, 'medianMs': None, 'fps': None, 'maxMs': None}
    median = statistics.median(deltas)
    return {
        'frames': len(deltas),
        'medianMs': median,
        'fps': round(1000 / median, 1),
        'maxMs': max(deltas),
    }


def measure(browser: Browser, url: str, width: int, height: int, settle: float) -> dict:
    browser.viewport(width, height, touch=(width < 768))
    browser.goto(url, settle=settle)
    snap = browser.evaluate(SNAPSHOT, await_promise=False)
    snap['viewport'] = f'{width}x{height}'
    snap['idle'] = frame_stats(browser)
    snap['scrollLock'] = browser.evaluate(LOCK_COST, await_promise=False)
    return snap


def render(label: str, rows: list[dict]) -> str:
    out = [f'=== {label} ===']
    for r in rows:
        idle = r['idle']
        lock = r['scrollLock']
        out += [
            f'  {r["viewport"]}',
            f'    DOM nodes            {r["domNodes"]}',
            f'    .media-item rendered {r["rendered"]}   on screen {r["onScreen"]}',
            f'    document height      {r["scrollHeight"]}px',
            f'    still opacity 0      {r["stillTransparent"]}',
            f'    max entrance delay   {r["maxDelaySeconds"]}s',
            f'    idle frame           {idle["medianMs"]}ms '
            f'(~{idle["fps"]} fps, {idle["frames"]} frames)',
            f'    scroll-lock relayout apply {lock["apply"]}ms release {lock["release"]}ms',
        ]
    return '\n'.join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:18091/')
    parser.add_argument('--label', default='measurement')
    parser.add_argument('--settle', type=float, default=22.0, help='seconds to wait after navigate')
    parser.add_argument('--json-out', help='also write the raw numbers here')
    args = parser.parse_args()

    browser = Browser(profile='/tmp/glimpse-grid-metrics')
    try:
        rows = [
            measure(browser, args.url, 390, 844, args.settle),
            measure(browser, args.url, 1280, 900, args.settle),
        ]
    finally:
        browser.close()

    print(render(args.label, rows))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({'label': args.label, 'rows': rows}, indent=2))


if __name__ == '__main__':
    main()
