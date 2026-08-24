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

`config/entrypoint.sh` does exactly two things:

1. **Validate and normalise the environment.** Detect which servers have
   credentials, resolve `PRIMARY_SERVER` (correcting it if it names a server with
   no credentials), apply defaults for `APP_TITLE`, `CRON_SCHEDULE`, and
   `SORT_BY_DATE_ADDED`, install the crontab, and create the per-server data
   directories.
2. **Write `/app/web/config.json`.**

```json
{
  "appTitle": "Glimpse",
  "primaryServer": "plex",
  "servers": ["plex", "jellyfin"],
  "sortByDateAdded": false
}
```

That file is the whole interface between the container and the frontend. The app
fetches it once at boot, sets `data-server="<primaryServer>"` on `<html>`, and
CSS custom properties do the per-server theming from there.

**The entrypoint must never edit a file under `/app/web` other than
`config.json`.** The previous implementation rewrote `index.html` with `sed` on
every boot — injecting per-server themes and a server dropdown, then running
repair functions to clean up the corruption it had caused. That approach produced
most of this project's historical bugs. If something appears to require it, that
is a spec change to `application-shell`, not a wiring decision. See
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
