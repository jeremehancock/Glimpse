## ADDED Requirements

### Requirement: The boot fetch is skipped when a server's fetch inputs are unchanged

The entrypoint SHALL decide, per server, whether to run that server's fetch at
boot. It SHALL run the fetch when the server has no recorded fingerprint, or when
its recorded fingerprint does not match the current one. It SHALL skip the fetch
when they match.

The decision is per server and never global. A user adding Jellyfin to a
Plex-only install must get a Jellyfin import immediately without also paying for
a Plex re-import of data that is already correct.

The entrypoint's ordering does not change: the fetches it does run still complete
before `exec supervisord`, and nginx still does not exist until they do. It does
not need to move, because once a restart skips its fetches there is nothing slow
left ahead of supervisord and the site comes up in seconds on the snapshot
already on the volume. A first install still blocks on its first import, which is
the one case where there is nothing to serve regardless.

A fingerprint SHALL be derived from exactly the inputs that determine what a
snapshot contains: that server's URL, its token, and its library exclusion list.
No other input contributes. `APP_TITLE`, `TZ`, `PRIMARY_SERVER`,
`SORT_BY_DATE_ADDED` and `CRON_SCHEDULE` change how the snapshot is displayed or
when it is refreshed, never what is in it — they already take effect on restart
without an import, and importing a whole library because a user renamed the
application would be a regression rather than a safeguard.

The fingerprint SHALL be computed where the environment is already resolved, so
that "what is this server configured with" keeps a single implementation. The
entrypoint that this one replaced answered that question in three separate places
and they drifted.

The entire decision is keyed off state on the mounted volume. It introduces no
environment variable, and it MUST NOT: `docker-compose.yml` is frozen, and a
variable the application reads that an existing user's file does not set turns a
fallback into a decision someone has to make on purpose.

#### Scenario: An unchanged restart skips the fetch

- **WHEN** the container restarts with a server whose URL, token, and exclusion
  list are unchanged, and whose fingerprint was recorded by a previous successful
  import
- **THEN** the entrypoint SHALL NOT run that server's fetch, and SHALL say on
  stdout that it was skipped

#### Scenario: A changed token forces a fetch

- **WHEN** the container restarts with a server whose token differs from the one
  in its recorded fingerprint
- **THEN** the entrypoint SHALL run that server's fetch

#### Scenario: A changed exclusion list forces a fetch

- **WHEN** the container restarts with `PLEX_EXCLUDE_LIBRARIES` changed from its
  recorded value
- **THEN** the entrypoint SHALL run the Plex fetch, so that the exclusion takes
  effect on restart rather than at the next scheduled run

#### Scenario: A display-only setting does not force a fetch

- **WHEN** the container restarts with only `APP_TITLE`, `TZ`, `PRIMARY_SERVER`,
  `SORT_BY_DATE_ADDED`, or `CRON_SCHEDULE` changed
- **THEN** the entrypoint SHALL NOT run any fetch, and the changed setting SHALL
  still take effect

#### Scenario: A missing fingerprint is treated as a first install

- **WHEN** a server directory holds a snapshot but no fingerprint
- **THEN** the entrypoint SHALL run that server's fetch

#### Scenario: Servers are decided independently

- **WHEN** Jellyfin is newly configured on an install whose Plex fingerprint
  matches
- **THEN** the entrypoint SHALL run the Jellyfin fetch and SHALL skip the Plex
  fetch

#### Scenario: A skipped boot still serves the existing snapshot

- **WHEN** every configured server's fetch is skipped
- **THEN** the entrypoint SHALL reach supervisord without performing a fetch, and
  nginx SHALL serve the snapshot already on the volume

### Requirement: A fingerprint records a hash and never a credential

A server's fingerprint SHALL be stored as a hash of its fetch inputs. The stored
file MUST NOT contain any of those input values.

`/app/data` is served by nginx, so every file beneath it is downloadable by
anyone who can reach the port — which, this application being unauthenticated by
design, is anyone who can reach the port at all. A fingerprint holding the values
would put the media server's token in a publicly readable directory. A hash
detects a change just as reliably and discloses nothing, so there is no version
of this that needs the values on disk.

The fingerprint is a file the entrypoint generates. It lives under `/app/data`
alongside the snapshot it describes, never under `/app/web`, which holds only
authored files and the two the entrypoint generates there.

#### Scenario: The stored fingerprint discloses nothing

- **WHEN** a fingerprint has been written for a server
- **THEN** the file SHALL NOT contain that server's token, URL, or exclusion list

#### Scenario: A change to any input changes the fingerprint

- **WHEN** any one of a server's URL, token, or exclusion list differs
- **THEN** the computed fingerprint SHALL differ from the one computed before the
  change

#### Scenario: The same inputs produce the same fingerprint

- **WHEN** a fingerprint is computed twice from identical inputs
- **THEN** both SHALL be identical, so that an unchanged restart is recognised as
  unchanged

### Requirement: A fingerprint is written only after the import it describes succeeds

The entrypoint SHALL write a server's fingerprint only after that server's fetch
has completed successfully. A failed fetch SHALL leave the previously recorded
fingerprint, or the absence of one, untouched.

A fingerprint written before or regardless of the outcome asserts that the data
on disk was produced by the current settings. If the fetch then fails, that
assertion is false and the next restart acts on it: it sees a match, skips, and
withholds the user's settings change until a scheduled run happens to succeed.
Nothing reports this — the container starts cleanly, the site serves, and the
change the user made simply has not happened.

Leaving the record untouched on failure means the next restart retries, which is
the behaviour a user changing a setting expects from a restart.

#### Scenario: A failed boot fetch does not record a fingerprint

- **WHEN** a server's boot fetch fails
- **THEN** no new fingerprint SHALL be written for that server

#### Scenario: A retried boot fetch runs again

- **WHEN** the container restarts after a boot fetch that failed, with the same
  settings
- **THEN** the entrypoint SHALL run that server's fetch again

#### Scenario: A successful boot fetch records the fingerprint

- **WHEN** a server's boot fetch completes successfully
- **THEN** the entrypoint SHALL write that server's fingerprint, and a subsequent
  restart with unchanged settings SHALL skip the fetch

#### Scenario: One server's failure does not record another's

- **WHEN** a Plex boot fetch succeeds and a Jellyfin boot fetch fails
- **THEN** the Plex fingerprint SHALL be written and the Jellyfin fingerprint
  SHALL be unchanged
