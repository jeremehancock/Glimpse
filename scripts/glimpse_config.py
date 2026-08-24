#!/usr/bin/env python3
"""Resolve the environment into the files the frontend reads.

This replaces roughly 1,700 lines of shell that rewrote ``index.html`` with
``sed`` on every boot. The rule that replaces it is **generate, never mutate**:
everything here writes a whole file it owns, from a template it owns. Nothing
patches a file in place.

That distinction is the entire point. ``sed`` fails *silently* when a pattern
does not match, so an edit to the markup broke configuration at runtime with no
error; and it is not idempotent over its own output, so a restart re-substituted
already-substituted text. The old entrypoint shipped
``cleanup_duplicate_server_content()`` and ``fix_corrupted_files()`` to repair
the damage it did to itself. A whole-file write has neither problem: the output
depends on the environment and nothing else, including how many times the
container has started.

Run as a script to write both files:

    python3 glimpse_config.py --output /app/web

Import ``resolve()`` to get the same decisions as data, which is how the tests
reach it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Preference order, used in three places that must agree: which server is picked
# when PRIMARY_SERVER names one without credentials, which is picked when it is
# unset, and the order `servers` is listed in. Listing order is fixed rather than
# discovery-ordered so a switcher's entries do not reshuffle when a user adds a
# server.
SERVER_IDS = ('plex', 'jellyfin', 'emby')

DISPLAY_NAMES = {'plex': 'Plex', 'jellyfin': 'Jellyfin', 'emby': 'Emby'}

DEFAULT_APP_TITLE = 'Glimpse'
# Every six hours. Written as a constant rather than inline because the value
# contains the character pair that closes a C-style block comment, which has
# bitten this project in JS and CSS.
DEFAULT_CRON_SCHEDULE = '0 */6 * * *'

# Per-server chrome colour, used for both the manifest's theme_color and its
# background_color, and mirrored by the document's theme-color meta tag.
#
# These look transposed — the blue-tinted #0f1419 sits on green-branded Emby
# while blue-branded Jellyfin gets a neutral #101010 — and they are preserved
# exactly as the previous implementation had them. Changing them is a visible
# change to the PWA splash screen and the mobile address bar, so it is a
# decision for the user rather than a tidy-up. See the design document's open
# questions.
THEME_COLORS = {'plex': '#131313', 'jellyfin': '#101010', 'emby': '#0f1419'}


class NoServerConfiguredError(RuntimeError):
    """Raised when no media server has both a URL and a token.

    Starting anyway would serve an empty library, which is indistinguishable
    from a correctly configured server that happens to hold no media — so this
    is fatal rather than a warning.
    """


@dataclass(frozen=True)
class Server:
    """A media server that has both a URL and a token."""

    id: str
    name: str
    url: str
    token: str
    exclude_libraries: str

    @property
    def data_path(self) -> str:
        """Where this server's snapshot lives, relative to the web root."""
        return f'data/{self.id}'

    def to_config(self) -> dict[str, str]:
        """The public shape. Credentials never reach the browser."""
        return {'id': self.id, 'name': self.name, 'dataPath': self.data_path}


@dataclass(frozen=True)
class Resolved:
    """Every decision made from the environment, as data.

    Deliberately free of I/O so the resolution table — the highest-traffic
    conditional in the project — can be tested directly.
    """

    app_title: str
    primary_server: str
    servers: tuple[Server, ...]
    sort_by_date_added: bool
    cron_schedule: str
    # Messages the entrypoint prints. Carried rather than printed so resolution
    # stays pure; the warning text appears in support threads, so it is preserved
    # verbatim.
    warnings: tuple[str, ...]

    def config_json(self) -> dict[str, object]:
        """The contract the frontend reads."""
        return {
            'appTitle': self.app_title,
            'primaryServer': self.primary_server,
            'servers': [server.to_config() for server in self.servers],
            'sortByDateAdded': self.sort_by_date_added,
        }

    def manifest_json(self) -> dict[str, object]:
        """The PWA manifest, themed for the primary server.

        Generated rather than themed by custom properties because a manifest
        cannot reference CSS. Icon paths are absolute so they resolve the same
        from `/` and from `/jellyfin/`.
        """
        server = self.primary_server
        icon_dir = '/images' if server == 'plex' else f'/images/{server}'
        color = THEME_COLORS[server]

        return {
            'name': 'Glimpse Media Viewer',
            'short_name': 'Glimpse',
            'description': (
                'A sleek, responsive web application for browsing your '
                'Plex/Jellyfin/Emby media server'
            ),
            'start_url': '/',
            'display': 'standalone',
            'background_color': color,
            'theme_color': color,
            'orientation': 'any',
            'icons': [
                {
                    'src': f'{icon_dir}/android-chrome-192x192.png',
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any maskable',
                },
                {
                    'src': f'{icon_dir}/android-chrome-512x512.png',
                    'sizes': '512x512',
                    'type': 'image/png',
                },
            ],
        }

    def crontab(self) -> str:
        """The crontab installing one scheduled fetch per configured server.

        Generated here rather than assembled in shell so that "which servers are
        configured" has exactly one implementation. The previous entrypoint
        answered that question in three separate places — detection, the cron
        block, and the switcher — and they drifted.

        Emby is fetched by the Jellyfin fetcher: the APIs are compatible, which
        is why one adapter has always served both.
        """
        lines = ['PATH=/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin']
        for server in self.servers:
            fetcher = 'jellyfin' if server.id in ('jellyfin', 'emby') else 'plex'
            env_var = f'{server.id.upper()}_EXCLUDE_LIBRARIES'
            lines.append(
                f'{self.cron_schedule} root cd /app && '
                f'{env_var}="{server.exclude_libraries}" '
                f'/usr/local/bin/python /app/scripts/{fetcher}_data_fetcher.py '
                f'--url "{server.url}" --token "{server.token}" '
                f'--output /app/data/{server.id} '
                f'>> /var/log/cron.log 2>&1'
            )
        # cron requires a trailing newline or it silently ignores the last entry.
        return '\n'.join(lines) + '\n'


def _is_truthy(value: str | None) -> bool:
    """Read a boolean the way a compose file writes one.

    Accepts the spellings a user actually types. Anything else is false, which
    matches the previous shell comparison against the literal string "true".
    """
    return (value or '').strip().lower() in {'true', '1', 'yes', 'on'}


def _detect_servers(env: Mapping[str, str]) -> tuple[Server, ...]:
    """Every server with BOTH a URL and a token, in fixed preference order.

    Both are required: a URL without a token cannot be queried, and a token
    without a URL has nothing to query. Half-configured is not configured.
    """
    servers = []
    for server_id in SERVER_IDS:
        prefix = server_id.upper()
        url = (env.get(f'{prefix}_URL') or '').strip()
        token = (env.get(f'{prefix}_TOKEN') or '').strip()
        if not url or not token:
            continue
        servers.append(
            Server(
                id=server_id,
                name=DISPLAY_NAMES[server_id],
                url=url,
                token=token,
                exclude_libraries=(env.get(f'{prefix}_EXCLUDE_LIBRARIES') or '').strip(),
            )
        )
    return tuple(servers)


def _resolve_primary(requested: str, servers: tuple[Server, ...]) -> tuple[str, tuple[str, ...]]:
    """Pick the primary server, correcting a request that cannot be honoured.

    Preserved verbatim from the previous shell implementation, warning text
    included — the messages appear in support threads, so rewording them costs
    more than it gains.
    """
    configured = {server.id for server in servers}
    warnings: list[str] = []

    if requested in configured:
        return requested, ()

    # First configured server in preference order. Guaranteed to exist: the
    # caller raises NoServerConfiguredError before reaching here.
    fallback = next(sid for sid in SERVER_IDS if sid in configured)

    if requested in SERVER_IDS:
        # A recognised server that simply has no credentials. The phrasing names
        # the server being switched TO, not the one requested — preserved from
        # the shell implementation, where this exact wording appears in support
        # threads.
        warnings.append(
            f'Warning: PRIMARY_SERVER set to {requested!r} but only '
            f'{DISPLAY_NAMES[fallback]} credentials provided'
        )
        warnings.append(f'Auto-switching PRIMARY_SERVER to {fallback!r}')
        warnings.append(f'PRIMARY_SERVER changed from {requested!r} to {fallback!r}')
    else:
        warnings.append(
            f'PRIMARY_SERVER not set or invalid, defaulting to {fallback!r} '
            'based on available credentials'
        )

    return fallback, tuple(warnings)


def resolve(env: Mapping[str, str]) -> Resolved:
    """Turn the environment into every decision the container needs.

    Pure: no I/O, no reads of the real environment, no printing. Raises
    NoServerConfiguredError when nothing is usable.
    """
    servers = _detect_servers(env)
    if not servers:
        raise NoServerConfiguredError(
            'Error: No valid credentials provided for any media server\n'
            'Please set PLEX_URL/PLEX_TOKEN, JELLYFIN_URL/JELLYFIN_TOKEN, '
            'or EMBY_URL/EMBY_TOKEN'
        )

    requested = (env.get('PRIMARY_SERVER') or '').strip().lower()
    primary, warnings = _resolve_primary(requested, servers)

    app_title = (env.get('APP_TITLE') or '').strip() or DEFAULT_APP_TITLE
    cron_schedule = (env.get('CRON_SCHEDULE') or '').strip() or DEFAULT_CRON_SCHEDULE

    return Resolved(
        app_title=app_title,
        primary_server=primary,
        servers=servers,
        sort_by_date_added=_is_truthy(env.get('SORT_BY_DATE_ADDED')),
        cron_schedule=cron_schedule,
        warnings=warnings,
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write JSON atomically.

    Through a temporary file in the same directory, then rename. A rename within
    one filesystem is atomic, so nginx never serves a half-written file — which
    matters because config.json is what the smoke test reads to decide the boot
    finished. A partial file would report success for an incomplete boot.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + '\n'

    # Same directory as the target, so the rename below stays within one
    # filesystem and is therefore atomic.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # Readable by nginx. mkstemp creates at 0600.
        tmp_path.chmod(0o644)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def write_files(resolved: Resolved, output_dir: Path) -> None:
    """Write config.json and manifest.json — the only two generated files."""
    _write_json(output_dir / 'config.json', resolved.config_json())
    _write_json(output_dir / 'manifest.json', resolved.manifest_json())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Generate config.json and manifest.json from the environment.'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('/app/web'),
        help='Directory to write into (default: /app/web)',
    )
    parser.add_argument(
        '--crontab',
        type=Path,
        default=None,
        help='Also write the generated crontab to this path',
    )
    args = parser.parse_args(argv)

    try:
        resolved = resolve(os.environ)
    except NoServerConfiguredError as exc:
        print(exc, file=sys.stderr)
        return 1

    for warning in resolved.warnings:
        print(warning)

    print(f'Using PRIMARY_SERVER: {resolved.primary_server}')
    print(f'Using application title: {resolved.app_title}')
    print(f'Default sort by date added: {str(resolved.sort_by_date_added).lower()}')
    print(f'Configured servers: {", ".join(s.id for s in resolved.servers)}')

    try:
        write_files(resolved, args.output)
        if args.crontab is not None:
            args.crontab.write_text(resolved.crontab(), encoding='utf-8')
            args.crontab.chmod(0o644)
    except OSError as exc:
        print(f'Error: could not write configuration to {args.output}: {exc}', file=sys.stderr)
        return 1

    print(f'Wrote {args.output / "config.json"} and {args.output / "manifest.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
