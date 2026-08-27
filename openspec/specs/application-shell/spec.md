# application-shell Specification

## Purpose
TBD - created by archiving change replace-boot-time-html-rewriting. Update Purpose after archive.
## Requirements
### Requirement: The entrypoint generates files and never mutates authored ones

The container entrypoint SHALL produce its output by writing whole files it
owns. It MUST NOT modify, patch, or perform in-place substitution on any file
under `/app/web` that is authored in this repository.

Exactly two files are generated: `/app/web/config.json` and
`/app/web/manifest.json`. Every other file under `/app/web` — `index.html`,
`sw.js`, `offline.html`, and everything under `images/` — is read-only at
runtime.

The distinction is not stylistic. A whole-file write is deterministic and its
result does not depend on how many times the container has started; an in-place
substitution over its own prior output is neither, which is why the previous
implementation shipped repair passes for its own corruption.

#### Scenario: Authored files are byte-identical after boot

- **WHEN** the container starts with any combination of environment variables
- **THEN** `index.html`, `sw.js`, `offline.html`, and every file under
  `images/` SHALL be byte-identical to the copies baked into the image

#### Scenario: Restarting produces identical generated output

- **WHEN** a container is started, stopped, and started again with an unchanged
  environment
- **THEN** `config.json` and `manifest.json` SHALL be byte-identical across both
  starts

#### Scenario: A partial write is never served

- **WHEN** generating `config.json` fails partway through
- **THEN** no partial file SHALL be visible at `/app/web/config.json`, the
  entrypoint SHALL exit non-zero, and the failure SHALL be reported on stdout

### Requirement: config.json is the container-to-frontend contract

The entrypoint SHALL write `/app/web/config.json` describing every decision the
frontend needs: the application title, the resolved primary server, the
configured servers, and the default sort order.

The `servers` array SHALL list only servers that have both a URL and a token,
each with its `id`, its display `name`, and its `dataPath`, in the fixed order
`plex`, `jellyfin`, `emby` — a fixed order so a switcher's entries do not
reshuffle when a server is added.

#### Scenario: Configured servers are described in full

- **WHEN** `PLEX_URL` and `PLEX_TOKEN` are set, and `JELLYFIN_URL` and
  `JELLYFIN_TOKEN` are set, and no Emby credentials are set
- **THEN** `config.json` SHALL contain `servers` with exactly two entries, Plex
  first, each carrying `id`, `name`, and `dataPath` of `data/<id>`

#### Scenario: A server with only a URL is not configured

- **WHEN** `EMBY_URL` is set but `EMBY_TOKEN` is empty or unset
- **THEN** Emby SHALL NOT appear in `servers`

#### Scenario: Defaults are applied and reported

- **WHEN** `APP_TITLE`, `CRON_SCHEDULE`, and `SORT_BY_DATE_ADDED` are unset
- **THEN** `config.json` SHALL carry `appTitle` of `Glimpse` and
  `sortByDateAdded` of `false`, and the cron schedule SHALL default to
  `0 */6 * * *`

#### Scenario: Sort default is a boolean, not a string

- **WHEN** `SORT_BY_DATE_ADDED` is set to `true`
- **THEN** `config.json` SHALL carry `sortByDateAdded` as the JSON boolean
  `true`

### Requirement: The frontend reads its configuration once and fails loudly

The application SHALL fetch `config.json` exactly once at boot and read it into
a single store. It MUST NOT re-fetch it, and MUST NOT read configuration from
any second source.

If `config.json` cannot be fetched or cannot be parsed, the application SHALL
render an error naming the file. It MUST NOT fall back to built-in defaults —
a silent fallback reproduces the failure being removed, presenting a
misconfigured install as a working one showing the wrong library.

#### Scenario: Configuration is fetched once

- **WHEN** the application boots and the user switches tabs, searches, sorts,
  filters, and opens an item
- **THEN** exactly one request for `config.json` SHALL have been made

#### Scenario: A missing configuration file is reported

- **WHEN** `config.json` returns a non-success status
- **THEN** the application SHALL display an error message naming `config.json`
  and SHALL NOT display a media grid

#### Scenario: A malformed configuration file is reported

- **WHEN** `config.json` is served but is not valid JSON
- **THEN** the application SHALL display an error message naming `config.json`
  and SHALL NOT display a media grid

### Requirement: The container refuses to start without a usable server

The entrypoint SHALL exit non-zero, with a message naming the variables it
expected, when no media server has both a URL and a token.

Starting successfully with nothing to show would present an empty library that
is indistinguishable from a correctly configured server with no media.

#### Scenario: No credentials at all

- **WHEN** the container starts with no URL and token pair set for any server
- **THEN** the entrypoint SHALL exit non-zero and SHALL print a message naming
  `PLEX_URL`/`PLEX_TOKEN`, `JELLYFIN_URL`/`JELLYFIN_TOKEN`, and
  `EMBY_URL`/`EMBY_TOKEN`

#### Scenario: An unreachable server is not a configuration failure

- **WHEN** the container starts with `PLEX_URL` and `PLEX_TOKEN` set to values
  that cannot be reached
- **THEN** the entrypoint SHALL complete, nginx SHALL serve the application, and
  `config.json` SHALL list Plex as configured

### Requirement: A scheduled fetch is installed for each configured server

The entrypoint SHALL install one cron entry per configured server, on the
schedule given by `CRON_SCHEDULE`, passing that server's URL, token, exclusion
list, and output directory to the appropriate fetcher.

Emby SHALL be fetched by the Jellyfin fetcher, their APIs being compatible.

#### Scenario: One entry per configured server

- **WHEN** Plex and Emby are configured and Jellyfin is not
- **THEN** the installed crontab SHALL contain exactly two entries, one writing
  to `/app/data/plex` and one writing to `/app/data/emby`

#### Scenario: The configured schedule is used

- **WHEN** `CRON_SCHEDULE` is set to `30 2 * * *`
- **THEN** every installed cron entry SHALL use that schedule

#### Scenario: Exclusions reach the fetcher

- **WHEN** `PLEX_EXCLUDE_LIBRARIES` is set to `Home Videos,4`
- **THEN** the Plex cron entry SHALL pass that value through to the fetcher

### Requirement: nginx serves one application for every server route

nginx SHALL serve the single authored `index.html` for `/` and for the
`/plex/`, `/jellyfin/`, and `/emby/` sub-routes. It MUST NOT require a
per-server copy of the page to exist on disk.

The snapshot SHALL remain available under `/data/`.

#### Scenario: A sub-route serves the application

- **WHEN** a request is made to `/jellyfin/` on an install where Jellyfin is
  configured
- **THEN** nginx SHALL respond with the application

#### Scenario: The snapshot is served

- **WHEN** a request is made to `/data/plex/movies.json` and that file exists
- **THEN** nginx SHALL serve it

#### Scenario: Data paths resolve identically from every route

- **WHEN** the application is loaded from `/` and from `/jellyfin/`
- **THEN** both SHALL resolve a poster to the same absolute URL

### Requirement: Readiness is observable

A running container SHALL expose evidence that its entrypoint completed, distinct
from evidence that nginx is listening. nginx serves the application from the
image layer whether or not the boot script finished, so a successful response
from `/` proves only liveness.

`config.json` SHALL serve this purpose: its presence and validity mean the
entrypoint ran to completion.

#### Scenario: A completed boot is observable

- **WHEN** the entrypoint has completed and nginx is serving
- **THEN** a request to `/config.json` SHALL return valid JSON containing
  `primaryServer`

### Requirement: The configuration is read once, from the container, or reported

The frontend SHALL continue to read its configuration exactly once at boot, into
a single store, from `/config.json`, and SHALL report any failure to read it
rather than defaulting around it.

There is no exception for an unreachable container, and this is worth stating
because **one was built and withdrawn**. `serve-the-library-offline` retained the
last configuration the container returned, so an installed app could open away
from its network. It worked, and it was reverted: the app has no way to tell the
user whether the library they are then shown is current, and presenting one that
may be out of date is the same ambiguity this requirement exists to refuse.

Reintroducing it is a product decision, not a wiring one.

A note for whoever tries: the boot read is a **synchronous** request, and a
browser dispatches no fetch event for one. The service worker never sees it and
cannot answer it from a cache. Any retention would have to live somewhere
readable before first paint, because the theme is applied from it and applying it
later is a visible flash of the wrong brand.

#### Scenario: The container answers

- **WHEN** the container returns a valid configuration
- **THEN** the app SHALL start from it

#### Scenario: The container answers badly

- **WHEN** the container answers with an error status, or with a body that is not
  valid configuration
- **THEN** the app SHALL report the configuration as unavailable

#### Scenario: The container cannot be reached

- **WHEN** the configuration request cannot reach the container
- **THEN** the app SHALL report the configuration as unavailable, and SHALL NOT
  start from any previously held copy

#### Scenario: Configuration is still read once

- **WHEN** the app is running
- **THEN** it SHALL NOT re-read the configuration, from cache or from the
  network, and there SHALL be no second source for any setting

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

