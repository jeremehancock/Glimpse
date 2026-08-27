## Why

Refreshing the library snapshot takes the site down, and it does so twice over.

**Every cron run puts the site into an error state for the whole import.** Both
fetchers call `clean_existing_data()` as their first act, deleting `movies.json`
and `tvshows.json` before a single item has been fetched, and only writing the
replacements at the very end. For the minutes in between, nginx is running and
the page shell loads, but the snapshot it asks for is a 404 — so the viewer gets
"Failed to load movie data. Please try again later." The site is not down; it is
*broken*, which is harder to recognise and harder to diagnose.

The same delete-first ordering means a **failed** run destroys the library. Both
fetchers return early when they cannot reach their server, by which point the
files are already gone and nothing puts them back. A media server that happens to
be rebooting at 06:00 leaves the viewer with an empty library until a later run
succeeds.

**Every container restart re-runs the full import.** The entrypoint fetches
unconditionally before starting supervisord, so nginx does not exist until the
import finishes — the container genuinely refuses connections on 9090 for the
duration. A user who rebuilds the container to change nothing at all still pays
for a complete re-import of a library that is already sitting on the volume.

## What Changes

- **A snapshot is replaced whole, or not at all.** Each fetcher writes
  `movies.json` and `tvshows.json` to a temporary file in the same directory and
  renames it into place only after the run has succeeded. `clean_existing_data()`
  and its delete-first ordering are removed. A reader therefore always sees
  either the complete previous snapshot or the complete new one — never a 404,
  never a truncated body, never one file present and the other missing.
- **A failed fetch leaves the previous snapshot untouched.** This falls out of
  the same change: a run that gives up before writing has modified nothing.
- **The boot fetch is skipped per server when nothing that affects the snapshot
  has changed.** Each server directory carries a fingerprint of the settings that
  produced its last successful import. On boot the entrypoint compares; a match
  skips that server's fetch, a difference or a missing fingerprint runs it.
- **The fingerprint covers exactly the three variables that change what the
  snapshot contains** — `<SERVER>_URL`, `<SERVER>_TOKEN`, and
  `<SERVER>_EXCLUDE_LIBRARIES`. `APP_TITLE`, `TZ`, `PRIMARY_SERVER`,
  `SORT_BY_DATE_ADDED` and `CRON_SCHEDULE` affect display or scheduling only;
  they already take effect on restart without an import, and re-importing a large
  library because someone renamed the app would be a regression.
- **The fingerprint is a hash, never the values.** `/app/data` is served by nginx,
  so anything written there is downloadable by anyone who can reach the site. A
  file containing a token would be a credential leak; a hash detects change just
  as well and discloses nothing.
- **The fingerprint is written only after a successful import.** Writing it up
  front would leave a file claiming the settings are current while the data
  predates them, and the next restart would skip — silently withholding the
  user's change until cron happened to run.

Not changing: the entrypoint still runs its fetches before `exec supervisord`. It
does not need to move. Once a restart skips its fetches there is nothing slow
left ahead of supervisord, so the site comes up in seconds on the data already on
the volume. A genuine first install still blocks on its first import, which is
the one case where there is nothing to serve anyway.

**This change does not touch the frozen `docker-compose.yml` surface.** It adds
no environment variable and changes no variable's meaning. Every input it reads
is one an existing compose file already sets; the skip decision is keyed entirely
off state on the mounted volume. An existing user's compose file runs it
unchanged.

**Accepted behaviour change:** an install upgrading to this version has data but
no fingerprint, and a missing fingerprint is treated as a first install. That
upgrade therefore takes one blocking import — the last one it will ever take
unless one of the three fingerprinted variables changes. The alternative
(assuming the settings are unchanged and skipping) was considered and rejected:
it would silently swallow a settings change made in the same upgrade.

## Capabilities

### New Capabilities

None. Both capabilities below are on the map in `openspec/config.yaml`.

### Modified Capabilities

- `media-fetch`: how a snapshot is written to disk. Adds the requirement that a
  snapshot is published atomically and that a failed run leaves the previous one
  intact. This capability is on the map but has no spec file yet, so this delta
  seeds `openspec/specs/media-fetch/spec.md`.
- `application-shell`: what the entrypoint does at boot. Adds the per-server
  fingerprint, the skip decision, and the rule that the fingerprint is written
  only after a success and never contains a credential.

## Impact

**Code**

- `scripts/plex_data_fetcher.py` — remove `clean_existing_data()`, write via
  temp file and rename.
- `scripts/jellyfin_data_fetcher.py` — the identical change. Jellyfin and Emby
  share this one fetcher, so the fix must land in both fetchers or the Plex
  library gets a behaviour the other two do not.
- `scripts/glimpse_config.py` — compute the per-server fingerprint. It is already
  the single place that reads the environment and resolves which servers are
  configured; putting this anywhere else would give that question a second
  implementation, which is exactly how the previous entrypoint drifted.
- `config/entrypoint.sh` — compare the fingerprint, decide whether to run each
  fetch, write the fingerprint after a success.

**On-disk surface**

- One new file per server under `/app/data/<server>/`, holding a hash. The
  entrypoint generates it; it is not an authored file and nothing under
  `/app/web` is touched.

**Docs**

- `docs/docker.md` and the header comment in `config/entrypoint.sh` both describe
  the boot sequence as unconditionally running an initial fetch. Both go stale
  and are updated in the same commit.
- `README.md` — check whether it documents restart-to-reimport behaviour.

**Verification**

- `config/entrypoint.sh` changes require `make docker-smoke` locally; CI only
  builds the image after a push.

**Considered and deferred** — noted here so they are not re-derived later:

- Telling the frontend an import is in progress, so a first install shows
  "importing" rather than the generic load error. Needs a status contract between
  fetcher and page that does not exist today.
- Starting nginx before the boot fetch and importing in the background.
- Staggering the cron schedule across servers; today every configured server
  imports simultaneously.
- Writing `checksums.pkl` incrementally so an interrupted run does not lose its
  artwork bookkeeping and force a full re-download.
