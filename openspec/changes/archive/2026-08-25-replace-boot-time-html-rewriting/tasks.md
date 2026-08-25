## 1. The config generator

- [x] 1.1 Create `scripts/glimpse_config.py` with a pure function that takes an environment mapping and returns the resolved configuration: app title, primary server, configured servers, sort default, cron schedule. No I/O, so it is directly testable.
- [x] 1.2 Implement server detection — a server is configured only when both its URL and its token are non-empty.
- [x] 1.3 Implement `PRIMARY_SERVER` resolution, preserving the preference order `plex`, `jellyfin`, `emby`, the substitution warnings, and the unset/unrecognised fallbacks.
- [x] 1.4 Raise a distinct error when no server is configured, carrying the message that names all six variables.
- [x] 1.5 Add a CLI entry point that writes `config.json` and `manifest.json` to a target directory, writing to a temporary path and renaming so a partial file is never served.
- [x] 1.6 Emit `sortByDateAdded` as a JSON boolean, not a string.
- [x] 1.7 Build the manifest from the primary server: icon paths (`/images/` for Plex, `/images/<server>/` otherwise) and colours (Plex `#131313`, Jellyfin `#101010`, Emby `#0f1419`).

## 2. Tests for the generator

- [x] 2.1 Test the full `PRIMARY_SERVER` resolution table — every combination of requested server against every credential set, including unset and unrecognised values. This is the highest-traffic conditional in the project and currently has no test.
- [x] 2.2 Test that a URL without a token, and a token without a URL, both leave the server unconfigured.
- [x] 2.3 Test that no credentials at all raises, and that the message names all six variables.
- [x] 2.4 Test `servers` ordering is always `plex`, `jellyfin`, `emby` regardless of which are present.
- [x] 2.5 Test defaults: `APP_TITLE` of `Glimpse`, `sortByDateAdded` of `false`, cron of `0 */6 * * *`. Write the cron expression so it does not sit inside a `/* */` comment.
- [x] 2.6 Test manifest generation for each primary server — icon paths and both colour fields.
- [x] 2.7 Test that generating twice with an unchanged environment produces byte-identical output.

## 3. The entrypoint

- [x] 3.1 Rewrite `config/entrypoint.sh`: validate the environment, invoke the generator, install the crontab, create the per-server data directories, set permissions, start supervisord.
- [x] 3.2 Keep the existing data migration step for backward compatibility with pre-multi-server layouts.
- [x] 3.3 Install one cron entry per configured server, passing URL, token, exclusion list and output directory. Emby uses the Jellyfin fetcher.
- [x] 3.4 Delete `apply_jellyfin_theme`, `apply_emby_theme`, `create_themed_offline`, `create_themed_manifest`, `create_server_index`, `replace_toggle_with_dropdown`, `configure_multi_server_dropdown`, `cleanup_duplicate_server_content`, `remove_server_toggle`, and `fix_corrupted_files`.
- [x] 3.5 Verify no `sed`, `awk`, or in-place edit remains that targets any file under `/app/web`.
- [x] 3.6 Exit non-zero with a readable message if the generator fails.

## 4. nginx routing

- [x] 4.1 Add a location matching `/plex/`, `/jellyfin/` and `/emby/` that serves the single `index.html`.
- [x] 4.2 Confirm `/data/` still serves the snapshot and that `config.json` is served without caching, so a restart with new settings is picked up on the next load.
- [x] 4.3 Remove the `try_files` behavior that depended on per-server copies existing.

## 5. Frontend adapter

- [x] 5.1 Add an inline `<head>` script that reads the active server from the path and sets `data-server` on `<html>` before first paint. Mark the whole adapter in-file with this change's name as its removal trigger.
- [x] 5.2 Add the three palettes to the stylesheet as `:root[data-server='...']` blocks; remove the hardcoded Plex values from `:root`.
- [x] 5.3 Fetch `config.json` once at boot into a single store; render an error naming the file if it is missing or malformed, and do not fall back to defaults.
- [x] 5.4 Apply `appTitle` to the document title (with the active server name appended) and to the header heading (without it).
- [x] 5.5 Resolve data paths against an absolute root so `/` and `/jellyfin/` produce identical URLs.
- [x] 5.6 Apply `sortByDateAdded` as the initial sort, replacing the `sed` substitution of `currentSortMethod`.
- [x] 5.7 Point the icon links and the header logo at the active server's icon set.
- [x] 5.8 Rewrite `toggleServer()` to switch using `config.json` rather than a hardcoded Plex↔Jellyfin pair, fixing the Plex+Emby case. Show a toggle for two servers, a menu for three, nothing for one.
- [x] 5.9 Redirect to `/` when the path names a server that is not configured.

## 6. Service worker and offline page

- [x] 6.1 Establish that one server's view is never served for another. Implementation showed a per-server cache key is unnecessary — every route returns identical markup — so the requirement was reworded via `/opsx:update` and the guarantee rests on identical markup plus the version bump in 6.2.
- [x] 6.2 Bump the cache version so the first load after upgrading discards entries cached under the old scheme.
- [x] 6.3 Remove the `CLEAR_THEMED_CACHE` message handler and its caller.
- [x] 6.4 Theme `offline.html` from the same custom properties; confirm it is no longer generated at boot.

## 7. Gates and CI

- [x] 7.1 Add the `config.json` readiness assertion to `.github/workflows/ci.yml`, replacing the comment that reserves it.
- [x] 7.2 Extend `make docker-smoke` to request each configured server's route and assert the response carries that server's data path.
- [x] 7.3 Remove `scripts/plex_data_fetcher.py` and `scripts/jellyfin_data_fetcher.py` from the ruff `extend-exclude` list only if this change ends up touching them; otherwise leave the list alone for the fetcher change.
- [x] 7.4 Run `make check` and `make docker-smoke`; both must pass.

## 8. Documentation

- [x] 8.1 Restate the entrypoint rule in `CLAUDE.md` as *generate, never mutate*, listing `config.json` and `manifest.json` as the two generated files.
- [x] 8.2 Update `docs/docker.md`: the entrypoint contract, the `config.json` schema with the `servers` array, and the manifest.
- [x] 8.3 Update the README project-structure tree and the "How It Works" section — theming is no longer described as rewriting the interface at boot.
- [x] 8.4 Confirm the README still documents the sub-route URLs as supported.

## 9. Validation

- [x] 9.1 Verify authored files are byte-identical before and after a container start.
- [x] 9.2 Verify a stop/start cycle produces byte-identical `config.json` and `manifest.json`.
- [x] 9.3 Verify each palette renders, with no flash of the wrong brand on load. (Structurally verified: the boot script is parser-blocking, sits in `<head>` above the stylesheet, and all three `:root[data-server=...]` blocks exist with no hardcoded primary in `:root`. Visual confirmation belongs to 9.7.)
- [x] 9.4 Verify a direct request to each configured sub-route loads that server's library.
- [x] 9.5 Verify switching works for all three pairings, including Plex+Emby.
- [x] 9.6 Verify the snapshot is untouched — `checksums.pkl` still valid, no re-download triggered on the next scheduled run.
- [ ] 9.7 Push to `dev` and validate the `:dev` image against a real install with at least two servers configured.
