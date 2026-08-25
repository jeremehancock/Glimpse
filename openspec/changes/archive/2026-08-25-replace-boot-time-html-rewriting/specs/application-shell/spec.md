## ADDED Requirements

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
