# Spec Delta

## ADDED Requirements

### Requirement: A token may be read from a file named by a _FILE variable

When `<SERVER>_TOKEN` is unset or empty and `<SERVER>_TOKEN_FILE` is set, the
container SHALL use that file's contents, with surrounding whitespace removed,
as the token, for Plex, Jellyfin and Emby alike. A non-empty `<SERVER>_TOKEN`
SHALL always win, so an install that sets no `_FILE` variable behaves exactly
as before.

#### Scenario: The token comes from a file

- **WHEN** `JELLYFIN_URL` is set, `JELLYFIN_TOKEN` is unset, and
  `JELLYFIN_TOKEN_FILE` names a readable file holding `abc123` and a trailing
  newline
- **THEN** Jellyfin SHALL be configured with the token `abc123`, and its
  scheduled and boot fetches SHALL use it

#### Scenario: The plain variable wins

- **WHEN** `PLEX_TOKEN` is `from-env` and `PLEX_TOKEN_FILE` names a file
  holding `from-file`
- **THEN** Plex SHALL use `from-env` and the file SHALL NOT be read

#### Scenario: No _FILE variable is set

- **WHEN** the container starts with the variables of an unmodified
  `docker-compose.yml` and no `_FILE` variable
- **THEN** the configured servers, `config.json` and every fingerprint SHALL be
  identical to those produced before this change, and the crontab SHALL differ
  only in the Jellyfin and Emby entries naming their identity

#### Scenario: Moving a token into a file does not re-import the library

- **WHEN** an install that set `EMBY_TOKEN=abc123` restarts with
  `EMBY_TOKEN` unset and `EMBY_TOKEN_FILE` naming a file holding `abc123`
- **THEN** Emby's current fingerprint SHALL equal its recorded one and its boot
  fetch SHALL be skipped

### Requirement: An unusable token file stops the container

When `<SERVER>_TOKEN` is unset or empty and `<SERVER>_TOKEN_FILE` names a file
that cannot be read, or holds only whitespace, the entrypoint SHALL exit
non-zero with a message naming the variable and the path. It SHALL NOT start
with that server dropped, even when another server is configured.

A dropped server looks like a working install that simply has one server fewer.

#### Scenario: The named file does not exist

- **WHEN** `PLEX_URL` and `PLEX_TOKEN` are set, `JELLYFIN_URL` is set,
  `JELLYFIN_TOKEN` is unset, and `JELLYFIN_TOKEN_FILE` is
  `/run/secrets/missing`
- **THEN** the entrypoint SHALL exit non-zero and its message SHALL name
  `JELLYFIN_TOKEN_FILE` and `/run/secrets/missing`

#### Scenario: The named file is empty

- **WHEN** `EMBY_URL` is set, `EMBY_TOKEN` is unset, and `EMBY_TOKEN_FILE`
  names an empty file
- **THEN** the entrypoint SHALL exit non-zero and its message SHALL name
  `EMBY_TOKEN_FILE`

#### Scenario: The message does not disclose a token

- **WHEN** the entrypoint reports an unusable token file
- **THEN** its message SHALL NOT contain any token value from the environment
  or from any file

### Requirement: The boot fetch uses the same resolved settings as the crontab

The entrypoint's boot fetch SHALL run each configured server's fetcher with the
URL, token, exclusion list and identity resolved by the same step that writes
`config.json`, the crontab and the fingerprints. It SHALL NOT read the
`*_URL`, `*_TOKEN` or `*_EXCLUDE_LIBRARIES` variables a second time itself.

Two readings of one setting drift; a token supplied by file is the first case
where they would have disagreed.

#### Scenario: A server configured by file gets a boot fetch

- **WHEN** Jellyfin is configured through `JELLYFIN_TOKEN_FILE` and has no
  recorded fingerprint
- **THEN** the entrypoint SHALL run Jellyfin's boot fetch with the token from
  that file, and SHALL record its fingerprint only after that fetch succeeds

#### Scenario: Surrounding whitespace is removed in one place

- **WHEN** `JELLYFIN_TOKEN` is set to `abc123 ` with a trailing space
- **THEN** the boot fetch and the cron entry SHALL both use `abc123`
