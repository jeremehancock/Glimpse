"""Drive a real Chromium over the DevTools protocol.

Development tooling. Not shipped: the `Dockerfile` copies `scripts/`, `web/` and
`config/`, and nothing else.

WHY THIS EXISTS. `chromium --headless --virtual-time-budget=… --dump-dom` cannot
verify this app. Under `--virtual-time-budget`, `requestAnimationFrame` never
fires — and Alpine's transitions, the overlay scroll lock and the focus manager
all sequence on it. Every overlay sits frozen at `overlay-shut overlay-opening`,
so such a run proves overlays render *shut* and never opens one. Five bugs
reached the user that way while both the test suite and the browser check
reported everything fine.

This module has been rebuilt from scratch at least twice because it only ever
lived in a session transcript. It is committed so that stops happening.

    from tools.browser import Browser

    browser = Browser()
    try:
        browser.viewport(390, 844)          # test 1280 AND 390; they differ
        browser.goto('http://127.0.0.1:18081/')
        browser.evaluate("document.querySelector('.genre-button').click()")
        print(browser.evaluate("getComputedStyle(document.querySelector('.sheet')).alignItems"))
    finally:
        browser.close()

Requires `chromium` on PATH and `websocket-client` installed.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from collections.abc import Callable
from typing import Any

import websocket

DEFAULT_PORT = 9333


class Browser:
    """A Chromium instance with one page target attached.

    `--remote-allow-origins=*` is not optional: without it the CDP websocket
    handshake is rejected with a 403 that reads like the browser failed to start.
    Each instance needs its own `--user-data-dir`, or a second instance silently
    attaches to the first one's profile.
    """

    def __init__(
        self,
        profile: str = '/tmp/glimpse-cdp-profile',
        port: int = DEFAULT_PORT,
        binary: str = 'chromium',
    ) -> None:
        self.port = port
        self.proc = subprocess.Popen(
            [
                binary,
                '--headless=new',
                '--disable-gpu',
                '--no-sandbox',
                f'--remote-debugging-port={port}',
                '--remote-allow-origins=*',
                f'--user-data-dir={profile}',
                'about:blank',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.ws: websocket.WebSocket | None = None
        for _ in range(60):
            try:
                targets = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
                page = next(target for target in targets if target['type'] == 'page')
                self.ws = websocket.create_connection(
                    page['webSocketDebuggerUrl'],
                    origin='http://127.0.0.1',
                    suppress_origin=True,
                    timeout=30,
                )
                break
            except Exception:
                time.sleep(0.5)
        if self.ws is None:
            raise AssertionError(f'could not attach to {binary} on port {port}')
        self.message_id = 0

    def send(self, method: str, **params: Any) -> dict:
        """One CDP command. Blocks until the matching reply arrives.

        Replies are matched by id rather than taken in order, because the page
        emits unsolicited events on the same socket.
        """
        assert self.ws is not None
        self.message_id += 1
        self.ws.send(json.dumps({'id': self.message_id, 'method': method, 'params': params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get('id') == self.message_id:
                if 'error' in message:
                    raise AssertionError(f'{method}: {message["error"]}')
                return message.get('result', {})

    def evaluate(self, expression: str, await_promise: bool = True) -> Any:
        """Run JavaScript in the page and return it by value.

        `await_promise` defaults to True so an async IIFE can be passed straight
        in. Set it False for an expression that is not a promise — awaiting a
        plain value is an error, not a no-op.
        """
        result = self.send(
            'Runtime.evaluate',
            expression=expression,
            awaitPromise=await_promise,
            returnByValue=True,
        )
        if 'exceptionDetails' in result:
            raise AssertionError(result['exceptionDetails'].get('text', 'evaluate failed'))
        return result['result'].get('value')

    def goto(self, url: str, settle: float = 5.0) -> None:
        """Navigate, then wait.

        A fixed wait rather than a load event because what usually matters here
        lands after load: the service worker taking control, the grid rendering,
        an overlay finishing its transition. Raise `settle` before suspecting the
        app when a first run looks empty.
        """
        self.send('Page.navigate', url=url)
        time.sleep(settle)

    def viewport(self, width: int, height: int, touch: bool | None = None) -> None:
        """Resize, then VERIFY the resize took. Test at 1280 AND 390.

        `mobile=False` is deliberate and load-bearing. With `mobile=True`,
        Chromium applies mobile viewport handling — and a page without a
        `<meta name="viewport">` then falls back to a **980px layout viewport**,
        silently, whatever width was asked for. `innerWidth` reads 980,
        `matchMedia('(max-width: 767px)')` is false, and every measurement is a
        desktop measurement wearing a phone's label. Touch emulation is what was
        actually wanted, and it is set separately below.

        The assertion is the point. A viewport that quietly did not apply
        produces a green run against the wrong layout, which is the exact class
        of failure this whole module exists to prevent.
        """
        self.send(
            'Emulation.setDeviceMetricsOverride',
            width=width,
            height=height,
            deviceScaleFactor=1,
            mobile=False,
        )
        self.send(
            'Emulation.setTouchEmulationEnabled',
            enabled=width < 768 if touch is None else touch,
        )

        actual = self.evaluate('innerWidth', await_promise=False)
        if actual != width:
            raise AssertionError(
                f'viewport did not apply: asked for {width}px, page reports {actual}px. '
                f'Every measurement taken now would be against the wrong layout.'
            )

    def measure(self, selector: str) -> dict | None:
        """Rendered geometry and type metrics for one element.

        For questions like "is the gap below the handle the same on every tray".
        Read the rendered box, never the CSS — the eye measures to the glyph, and
        half-leading is part of that distance.
        """
        return self.evaluate(
            f"""(() => {{
              const el = document.querySelector({json.dumps(selector)});
              if (!el) return null;
              const rect = el.getBoundingClientRect();
              const style = getComputedStyle(el);
              return {{
                top: rect.top, bottom: rect.bottom, height: rect.height,
                left: rect.left, width: rect.width,
                paddingTop: style.paddingTop, marginTop: style.marginTop,
                fontSize: style.fontSize, lineHeight: style.lineHeight,
                display: style.display, alignItems: style.alignItems,
              }};
            }})()""",
            await_promise=False,
        )

    def close(self) -> None:
        try:
            if self.ws is not None:
                self.ws.close()
        finally:
            self.proc.terminate()
            self.proc.wait(timeout=10)


def nginx_requests(container: str) -> Callable[[], str]:
    """Capture what actually reached the container while something runs.

    Returns a function that yields the access-log lines written since this was
    called.

        since = nginx_requests('glimpse-dev')
        browser.goto(URL)
        log = since()
        posters = sum(1 for line in log.splitlines() if '/posters/' in line)

    USE THIS INSTEAD OF `PerformanceResourceTiming.transferSize` for any question
    about caching. `transferSize` reads 0 for anything a service worker handled,
    whether the worker went to the network or not — so "served from cache" and
    "fetched through the worker" are indistinguishable. That once reported the
    library snapshots as cache hits when every one of them had been fetched. The
    access log is the only witness that cannot be fooled.
    """
    before = subprocess.run(
        ['docker', 'exec', container, 'wc', '-l', '/var/log/nginx/access.log'],
        capture_output=True,
        text=True,
    ).stdout.split()[0]

    def since() -> str:
        return subprocess.run(
            [
                'docker',
                'exec',
                container,
                'tail',
                '-n',
                f'+{int(before) + 1}',
                '/var/log/nginx/access.log',
            ],
            capture_output=True,
            text=True,
        ).stdout

    return since
