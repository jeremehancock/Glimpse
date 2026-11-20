# Design

## Context

- `scripts/jellyfin_data_fetcher.py` serves both Jellyfin and Emby, but does not
  know which one it is talking to. It sets `X-Emby-Token` on one
  `requests.Session` that every call goes through, and it picks its exclusion
  list with `EMBY_EXCLUDE_LIBRARIES or JELLYFIN_EXCLUDE_LIBRARIES`.
- The settings are read twice. `glimpse_config.py` resolves the environment
  (stripping whitespace) into `config.json`, the crontab and the fingerprints.
  `entrypoint.sh` then reads `*_URL` / `*_TOKEN` / `*_EXCLUDE_LIBRARIES` again,
  unstripped, through `${!var}`, to run the boot fetch.
- Cron in the container does not inherit Docker's environment, which is why the
  crontab carries each server's resolved URL and token inline.

## Goals / Non-Goals

**Goals:**

- One place decides a server's URL, token, exclusions and identity; the boot
  fetch and the crontab both take them from there.
- Signing in is decided by identity, inside the one adapter.

**Non-Goals:**

- `_FILE` variants of anything other than the three tokens. URLs and exclusion
  lists are not secrets.
- Re-reading a token file at cron time. The token is resolved at boot, like
  every other setting; changing a Docker secret already requires recreating the
  container.
- Quoting hazards already present in the crontab (a token containing `"` or
  `%`). Unchanged by this work, and no real token format uses either.

## Decisions

### The fetcher takes `--server jellyfin|emby`, defaulting to `jellyfin`

The identity is an explicit argument rather than something inferred from the
output directory or URL. Inference from a path is a second, hidden meaning for a
setting that already has one. Defaulting to `jellyfin` matches the script's name
and keeps the README's hand-run Jellyfin command working; the README's Emby
commands gain `--server emby`.

The identity decides two things in one table: the sign-in header and the
exclusion variable. A per-identity dict, not an `if` in two places, so a third
difference has an obvious home.

### Jellyfin gets only the `Authorization` header

Alternative considered: send both `X-Emby-Token` and `Authorization` to both
servers, which would make the identity unnecessary for sign-in. Rejected:
whether current Jellyfin treats a present legacy header as an error or ignores
it is not something to depend on, and Emby's behavior with the `Authorization`
form is untested here. Each server gets the one form it is known to accept.

### Token files are resolved in `_detect_servers()`

Same function that already decides "has both a URL and a token", so a token from
a file is indistinguishable from one set directly by the time anything else
sees it: same `Server`, same `fetch_inputs()`, same fingerprint. Reading the
file is I/O, which `resolve()` has so far avoided; the reader is a parameter
defaulting to `Path.read_text`, so tests can pass a fake.

An unusable file raises a new `TokenFileError`, caught in `main()` beside
`NoServerConfiguredError` and exiting 1. Its message names the variable and the
path, never the contents. A `_FILE` set while the plain variable is also set is
ignored silently; the plain variable winning is documented, and printing about
it on every boot would be noise.

### The boot fetch runs through `glimpse_config.py --run-fetch <id>`

`--run-fetch` resolves the environment exactly as the boot step did, then
`os.execv`s the right fetcher with the server's URL, token, output directory and
`--server`, and `<ID>_EXCLUDE_LIBRARIES` set in its environment. `execv`
replaces the process, so the fetcher's exit status is the command's exit status
and the entrypoint's existing success/failure handling is unchanged. The crontab
line and the boot command are built from one helper, so they cannot disagree.

`run_initial_fetch` in the entrypoint shrinks to: is there a current
fingerprint for this server (that file existing *is* "configured", written by
the same resolution), does it need a fetch, run `--run-fetch`, record the
fingerprint on success. It keeps its fixed `plex jellyfin emby` order.

Alternative considered: teach the shell to read `_FILE` too. Rejected: that is a
second implementation of token resolution, the exact drift this file's header
comment was written about.

## Risks / Trade-offs

- [The `Authorization` form is rejected by some older Jellyfin] → Jellyfin has
  parsed `Authorization: MediaBrowser ...` since its fork from Emby; verify
  against a real current Jellyfin container in Docker, and against the oldest
  image that is easy to pull.
- [Emby sign-in regresses] → Emby path is unchanged in code; verify against a
  real Emby container too.
- [The new `_FILE` variables are an unpinned config surface] →
  `tests/test_glimpse_config.py` pins the three names and the precedence rule.
- [A token now appears in `execv` argv] → It already does today, through the
  entrypoint's `--token "$token"` and the crontab; no new exposure.

## Migration Plan

Nothing for users. Upgrading the image fixes a Jellyfin install with no
settings change. Rolling back restores the old behavior, including Jellyfin
being broken. An install that keeps its tokens in a `.env` file needs no change;
switching to `_FILE` is optional.
