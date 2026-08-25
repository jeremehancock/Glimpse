# The Docker image

Glimpse ships as one image: Debian slim + Python 3.13 + nginx + supervisord +
cron. There is no application server. nginx serves static files; cron runs the
Python fetchers on a schedule; the fetchers write a snapshot to a mounted volume
that nginx also serves.

```
                    ┌─────────────── container ───────────────┐
  media server ──►  │  cron ──► scripts/  ──►  /app/data  ◄── │ ──► ./data on the host
   (Plex/JF/Emby)   │                              ▲          │
                    │                     nginx ───┘          │
        browser ──► │  :80  ──►  /app/web (the app)           │
                    └─────────────────────────────────────────┘
```

## Read this before touching the image

**CI builds the image only *after* you push.** `make lint` and `make test` say
nothing about whether the container comes up. A broken `Dockerfile`,
`entrypoint.sh`, `nginx.conf`, or `supervisord.conf` gets caught by CI one round
trip later, and by then `:dev` may already be broken for whoever is testing it.

Build and probe locally first:

```bash
make docker-smoke
```

That builds the image, runs it with credentials that resolve to nothing, waits
for nginx, and checks that the entrypoint wrote its config. It cleans up after
itself.

## The two traps

**The Python version comes from the base image tag.** `FROM python:3.13-slim` is
what decides it. Editing package names or `pip` invocations alone doesn't upgrade
Python — it breaks the build. To bump:

1. Change the `FROM` tag.
2. Update `requires-python` in `pyproject.toml` and `target-version` under
   `[tool.ruff]`.
3. Update the `python-version` in `.github/workflows/ci.yml`.
4. Update the version named in `README.md` and `openspec/config.yaml`.
5. `make docker-smoke`, then `make check`.

All five, or something silently disagrees about which Python it is targeting.

**nginx serving a page does not prove the entrypoint ran.** nginx serves
`/app/web` from the image layer whether or not the boot script finished. A
container whose entrypoint died halfway still answers `200` on `/` with the files
baked in at build time. That is why the smoke test checks for the generated
`config.json` and not just for a `200` — liveness and readiness are different
questions here, and only the second one is interesting.

## The entrypoint contract

`config/entrypoint.sh` is about 130 lines and does four things: migrate an old
data layout, generate configuration, run an initial fetch, and start supervisord.

The generation step is delegated to `scripts/glimpse_config.py`, which resolves
the environment and writes three files:

| File | What it is |
| --- | --- |
| `/app/web/config.json` | The container-to-frontend contract |
| `/app/web/manifest.json` | The PWA manifest, themed for the primary server |
| `/etc/cron.d/media-cron` | One scheduled fetch per configured server |

All three come from one resolution so that "which servers are configured" has a
single implementation — the old script answered it in three places and they
drifted.

### `config.json`

```json
{
  "appTitle": "Glimpse",
  "primaryServer": "plex",
  "servers": [
    { "id": "plex", "name": "Plex", "dataPath": "data/plex" },
    { "id": "jellyfin", "name": "Jellyfin", "dataPath": "data/jellyfin" }
  ],
  "sortByDateAdded": false
}
```

`servers` lists only servers with **both** a URL and a token, always in the order
`plex`, `jellyfin`, `emby` — fixed, so a switcher's entries do not reshuffle when
a user adds a server. Credentials never appear; a test asserts that.

The app fetches this once at boot, sets `data-server="<active>"` on `<html>`, and
CSS custom properties do the theming from there. A missing or malformed file is
**reported to the user**, never defaulted around.

### Generate, never mutate

**The entrypoint must never edit an authored file.** It writes whole files it
owns, from templates it owns; it does not patch anything in place.

The previous implementation rewrote `index.html` with `sed` on every boot —
injecting per-server themes and a server dropdown, copying the page into
`/plex/`, `/jellyfin/` and `/emby/` — then ran
`cleanup_duplicate_server_content()` and `fix_corrupted_files()` to repair the
damage it had done to its own output. `sed` fails silently when a pattern does
not match, and is not idempotent over its own output, so correctness depended on
how many times the container had started.

`make docker-smoke` asserts the web root is clean after boot, and that every
route serves byte-identical markup. If something appears to require editing an
authored file, that is a spec change to `application-shell`, not a wiring
decision. See [CLAUDE.md](../CLAUDE.md).

### The server routes

`/`, `/plex/`, `/jellyfin/` and `/emby/` all serve the **same** `index.html`.
nginx aliases them; the app reads the active server from the first path segment
and falls back to `primaryServer` at the root. A path naming an unconfigured
server redirects to `/`.

Four things in `config/nginx.conf` are load-bearing:

- **`location ^~ /data/`** — the `^~` matters. Without it nginx checks the regex
  location for image extensions *first*, so `/data/plex/posters/1.jpg` would
  resolve against the document root instead of the alias.
- **`location = /config.json`** with `no-store` — a restart with new settings has
  to take effect on the next load, not whenever a cached copy expires.
- **`location = /sw.js`** with `no-cache` — the exact match is what outranks the
  `\.(css|js|…)$` regex below it, which used to hand the service worker a 7-day
  cache. That is the worst file here to hold: it is the code that decides what
  every other response may serve, so a stale copy freezes the caching policy of
  the whole app *and* withholds the upgrade that would correct it.
- **`location ^~ /assets/`** with `no-cache` — same collision, same `^~` trick as
  `/data/`. These filenames carry no content hash and never will, because nothing
  under `web/` is built or bundled: a changed stylesheet keeps its URL. Under the
  old 7-day cache every client stayed pinned to the CSS and JS of the build it
  first loaded while `index.html` went on upgrading, so new markup ran on old
  behavior indefinitely.

  `no-cache` means *revalidate*, not "do not store" — nginx answers 304 from the
  ETag, so correctness costs one conditional request. `/images/` and the artwork
  under `/data/` keep their 7-day cache; those are genuinely static.

  This pairs with `networkFirstWithCacheFallback` in `web/sw.js`, which fetches
  with `cache: 'reload'`. Both are needed and neither is sufficient: the worker's
  own `fetch()` consults the HTTP cache, so a long `max-age` here defeats a
  correct strategy — and a corrected header cannot retract an entry the browser
  was already told to keep for a week. See the caching table in
  [CLAUDE.md](../CLAUDE.md).

## The data volume

`./data:/app/data` holds the snapshot, one directory per server:

```
data/<server>/
├─ movies.json        # metadata for the movies grid
├─ tvshows.json       # metadata for the TV shows grid
├─ checksums.pkl      # MD5 per artwork file — what makes re-runs cheap
├─ posters/{movies,tvshows}/<id>.jpg
└─ backdrops/{movies,tvshows}/<id>.jpg
```

Two things to be careful with:

- **`checksums.pkl` is what stops every run re-downloading the library.**
  Invalidating it — a format change, a path change, a different id scheme — turns
  the next scheduled run into a full re-fetch of every poster and backdrop. For a
  large library over a slow link that is hours of traffic against the user's
  media server. Any change to the id scheme or the on-disk layout needs a
  migration that preserves it, not just a new format.
- **Files must be readable by nginx.** The fetchers set permissions explicitly
  after writing. A poster that downloads successfully and then 403s is this.

## Debugging a running container

```bash
docker logs -f glimpse-media-viewer          # entrypoint + supervisord + cron
docker exec -it glimpse-media-viewer bash

# Inside:
cat /app/web/config.json                     # what the entrypoint decided
crontab -l; cat /etc/cron.d/media-cron       # is the schedule installed?
ls -la /app/data/plex/                       # did the fetcher write anything?
python3 /app/scripts/plex_data_fetcher.py --help
```

Run a fetcher by hand to watch it work — `print()` output is the interface, and
`docker logs` is where a user sees an import run:

```bash
docker exec glimpse-media-viewer python3 /app/scripts/plex_data_fetcher.py \
  --url "$PLEX_URL" --token "$PLEX_TOKEN" --output /app/data/plex
```

## Multi-arch

The publish workflow builds `linux/amd64` and `linux/arm64` via QEMU. `make
docker-smoke` builds your native architecture only — fine for a smoke test, but
an arm64-specific failure will not appear until CI runs. Anything touching
compiled dependencies deserves a look at the publish job's log rather than a
green local build.
