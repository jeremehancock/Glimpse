# Tasks

## 1. Confirm the defect against a real server

- [x] 1.1 Start a local current `jellyfin/jellyfin` container, complete its setup wizard over the API and create an API key; verify `GET /Users` returns 401 with `X-Emby-Token` and 200 with `Authorization: MediaBrowser Token="..."`. Record the Jellyfin version in the PR. If `X-Emby-Token` is NOT rejected, stop and report back before changing code.

## 2. Sign in by identity

- [x] 2.1 In `scripts/jellyfin_data_fetcher.py`, add `--server jellyfin|emby` (default `jellyfin`) and a per-identity table giving the sign-in header and the exclusion variable; Jellyfin sends only `Authorization: MediaBrowser Token="<token>"`, Emby only `X-Emby-Token`. Verify with the tests in 2.3.
- [x] 2.2 Choose the exclusion variable from the identity instead of `EMBY_EXCLUDE_LIBRARIES or JELLYFIN_EXCLUDE_LIBRARIES`. Verify with the tests in 2.3.
- [x] 2.3 Add `tests/test_jellyfin_identity.py`: the session headers for each identity (and that Jellyfin carries no `X-Emby-Token`), the default identity, and each identity reading only its own exclusion variable. Verify `make test` passes.

## 3. Token files and one resolution for every fetch

- [x] 3.1 In `scripts/glimpse_config.py`, resolve `<SERVER>_TOKEN_FILE` in `_detect_servers()` when `<SERVER>_TOKEN` is empty (strip the contents); raise `TokenFileError` naming the variable and path for an unreadable or blank file; catch it in `main()` and exit 1. Verify with the tests in 3.4.
- [x] 3.2 Build each server's fetch command in one helper used by both `crontab()` and a new `--run-fetch <id>` option that `os.execv`s the fetcher (passing `--server` for Jellyfin/Emby and `<ID>_EXCLUDE_LIBRARIES` in the environment). Verify with the tests in 3.4.
- [x] 3.3 In `config/entrypoint.sh`, make `run_initial_fetch` take only the server id, treat `$FINGERPRINT_DIR/<id>` existing as "configured", and run `glimpse_config.py --run-fetch <id>`; keep the fingerprint-after-success logic and the `plex jellyfin emby` order. Verify `make docker-smoke` passes.
- [x] 3.4 Extend `tests/test_glimpse_config.py`: a token from a file (with trailing newline), the plain variable winning without the file being read, missing and blank files raising with the variable and path and no token in the message, a file-sourced token giving the same fingerprint as the same token set directly, an unchanged result for the stock compose variables, the crontab carrying `--server` for Jellyfin and Emby, and the `--run-fetch` command matching the cron command. Verify `make test` passes.
- [x] 3.5 Update `README.md` (a section on keeping tokens out of the compose file: `.env` substitution, which needs nothing from Glimpse, and `_FILE` with Docker secrets, using only the variable names from `docker-compose.yml` and generic paths in examples; `--server emby` on the manual Emby commands; the three `_FILE` variables in the variable table) and `docs/docker.md` (the boot fetch now goes through `--run-fetch`). Verify every README command still matches the scripts' options.

## 4. End-to-end against real servers

- [x] 4.1 Build the image and run it against the local Jellyfin from 1.1 twice: once with `JELLYFIN_TOKEN`, once with `JELLYFIN_TOKEN_FILE` pointing at a mounted file. Verify both import (non-empty `movies.json`/`tvshows.json` for a seeded library, fingerprint recorded) and that the second boot with the same token skips the fetch.
- [x] 4.2 Run the image against a local `emby/embyserver` container with `EMBY_TOKEN` and verify the import still succeeds with `X-Emby-Token`.
- [x] 4.3 Run the image with `JELLYFIN_TOKEN_FILE` naming a missing file alongside a working Plex setting and verify the container exits non-zero with a message naming the variable and path.
- [x] 4.4 Run `make lint` and `make test` and verify both pass.

## Workflow follow-up

- `/ship` to commit, push to `dev` and let the `:dev` image build.
- Validate the `:dev` image against a real Jellyfin install before archive.
- Archive the change in the same PR, then publish.
