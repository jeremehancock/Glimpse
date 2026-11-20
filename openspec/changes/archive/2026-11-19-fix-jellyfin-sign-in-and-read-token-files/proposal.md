# Proposal

## Why

Glimpse signs in to Jellyfin with the old `X-Emby-Token` header, and current
Jellyfin no longer accepts it. Every Jellyfin fetch is now rejected, so a
Jellyfin library in Glimpse silently stops updating: the last good snapshot
keeps being served (as designed), but nothing new ever arrives, with a valid
key and nothing on screen to say so.

A second, smaller gap: Glimpse can only take a token as a plain environment
variable. The standard Docker way to hand a container a secret is a file
(`/run/secrets/...`) named by a `<NAME>_FILE` variable, and Glimpse ignores
those. Users who keep secrets out of their compose file have only the `.env`
route today, and nothing in the README says that route exists.

## What Changes

- **Jellyfin signs in with `Authorization: MediaBrowser Token="<token>"`.**
  This form is accepted by current Jellyfin and by older releases, so no
  Jellyfin user has to change anything.
- **Emby keeps `X-Emby-Token`**, exactly as today. Emby and Jellyfin remain one
  fetcher, which is now told which of the two identities it is talking to and
  signs in the way that identity expects.
- **Each identity reads its own exclusion list.** The fetcher currently prefers
  `EMBY_EXCLUDE_LIBRARIES` whenever it is set, even while fetching Jellyfin. On
  a container configured with both, the boot fetch of Jellyfin applies Emby's
  exclusions. Same root cause as the sign-in bug (the fetcher not knowing which
  identity it is), so it is fixed in the same place.
- **Optional token files.** `PLEX_TOKEN_FILE`, `JELLYFIN_TOKEN_FILE` and
  `EMBY_TOKEN_FILE` name a file whose contents are the token. They are read
  **only** when the matching `<SERVER>_TOKEN` is unset or empty, so an existing
  install behaves exactly as before. A token file that is named but cannot be
  read, or is empty, stops the container with a message naming the variable and
  the path, rather than quietly dropping that server.
- **The boot fetch uses the same resolved settings as everything else.** Today
  the entrypoint reads the URL and token from the environment a second time, in
  shell; a token supplied by file would never reach it. The boot fetch is now
  driven by the same resolution that writes `config.json`, the crontab and the
  fingerprints.
- **Docs:** the README gains a short section on keeping tokens out of the
  compose file, both with a `.env` file (works today, no Glimpse change needed)
  and with `_FILE` variables.

### The frozen compose surface

`docker-compose.yml` is **not** changed and `tests/test_compose_surface.py` is
not touched. The three `_FILE` variables are new things the app reads that a
user's file does not set, so their fallback is a decision made here on purpose:
**when a `_FILE` variable is unset, Glimpse behaves exactly as it does today.**
An existing user has to do nothing. Nothing about a working Plex or Emby
install changes, and a Jellyfin install starts working again on upgrade.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-fetch`: adds how each identity of the shared Jellyfin/Emby adapter
  signs in, and that each identity reads its own exclusion list.
- `application-shell`: adds reading a token from a file named by a `_FILE`
  variable, the failure rule for an unreadable one, and that the boot fetch uses
  the same resolved settings as the crontab.

## Impact

- `scripts/jellyfin_data_fetcher.py`: sign-in header chosen by identity; new
  `--server jellyfin|emby` option; exclusion variable chosen by identity.
- `scripts/glimpse_config.py`: token-file resolution; the crontab passes
  `--server`; a way to run one server's boot fetch from the resolved settings.
- `config/entrypoint.sh`: the boot fetch loop no longer reads `*_URL` /
  `*_TOKEN` itself. Needs `make docker-smoke`.
- `README.md`, `docs/docker.md`: token-file and `.env` documentation; manual
  fetch commands gain `--server`.
- Tests: new unit tests for header selection, exclusion selection and token
  files. No change to the compose-surface or fingerprint tests' fixtures: a
  token read from a file produces the same fingerprint as the same token set
  directly, so switching an install to a secrets file does not re-import it.
