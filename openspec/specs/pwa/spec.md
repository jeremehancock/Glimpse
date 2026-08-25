# pwa Specification

## Purpose
TBD - created by archiving change replace-boot-time-html-rewriting. Update Purpose after archive.
## Requirements
### Requirement: The manifest is generated for the primary server

The entrypoint SHALL generate `/app/web/manifest.json` describing the primary
server's identity: its icon set and its colours. The manifest is generated rather
than themed by custom properties because a manifest cannot reference CSS.

Icons SHALL resolve under `/images/<server>/` for Jellyfin and Emby and directly
under `/images/` for Plex. The 192px icon SHALL be marked `any maskable`.

Colours SHALL be `#101010` for Jellyfin, `#0f1419` for Emby, and `#131313` for
Plex, applied to both `background_color` and `theme_color`.

#### Scenario: Manifest for a non-default primary server

- **WHEN** the primary server is Jellyfin
- **THEN** `manifest.json` SHALL reference icons under
  `/images/jellyfin/` and SHALL carry `theme_color` and `background_color` of
  `#101010`

#### Scenario: Manifest for the default primary server

- **WHEN** the primary server is Plex
- **THEN** `manifest.json` SHALL reference icons directly under `/images/` and
  SHALL carry `theme_color` and `background_color` of `#131313`

#### Scenario: The manifest is installable

- **WHEN** the container has started with any configured server
- **THEN** `manifest.json` SHALL be valid JSON carrying `name`, `short_name`,
  `start_url`, `display` of `standalone`, and both a 192px and a 512px icon

### Requirement: The document theme colour matches the generated manifest

The `theme-color` meta value SHALL equal the generated manifest's `theme_color`
for the active server. The two drive the same surfaces — the mobile address bar
and the installed application's chrome — so a disagreement between them shows as
a colour change when the app is installed.

#### Scenario: Meta and manifest agree

- **WHEN** the active server is Emby
- **THEN** the document's `theme-color` SHALL be `#0f1419`, matching
  `manifest.json`

### Requirement: The service worker cache is keyed by active server

The service worker SHALL NOT serve one server's view in place of another's, and
SHALL change its cache version whenever the caching scheme changes, so that an
upgrade discards entries written under the previous one.

The separation is a property of the design rather than of the cache. Every route
returns byte-identical markup — the theme and the data paths are resolved at
runtime from `config.json` — so the route URLs alone are sufficient to keep
entries apart, and no server-specific cache key is required. Adding one would
store several identical copies of the same shell.

This is worth stating because it was not true before. Each route used to be a
physically different file with its theme and data paths substituted into the
markup at container start, so a cached entry really could carry the wrong
server's page, and the application had to race a cache-clearing message against
a navigation to avoid it. Removing that handshake is safe only for as long as the
markup stays identical across routes; a change that reintroduces per-route
differences in the served HTML must revisit this requirement.

#### Scenario: Switching servers does not serve a stale page

- **WHEN** the user views Plex, switches to Jellyfin, and reloads
- **THEN** the application SHALL show Jellyfin's library

#### Scenario: Upgrading discards caches from the previous scheme

- **WHEN** a client that cached the application under the previous scheme loads
  the upgraded application
- **THEN** the previously cached entries SHALL be discarded

#### Scenario: The cache-clearing message is no longer required

- **WHEN** the user switches servers
- **THEN** the application SHALL NOT depend on a message to the service worker
  completing before navigation

### Requirement: The offline page is themed by the same tokens as the application

The offline fallback SHALL take the active server's palette from the same custom
properties the application uses, and SHALL NOT be regenerated at boot.

#### Scenario: Offline page reflects the active server

- **WHEN** the primary server is Jellyfin and the offline page is shown
- **THEN** it SHALL be drawn in the Jellyfin palette

#### Scenario: The offline page is authored, not generated

- **WHEN** the container starts with any configuration
- **THEN** `offline.html` SHALL be byte-identical to the copy baked into the
  image

### Requirement: The application remains available offline

The service worker SHALL cache the application shell and serve it when the
network is unavailable, falling back to the offline page for navigations it
cannot satisfy.

#### Scenario: The shell is served offline

- **WHEN** the application has been loaded once and the network is unavailable
- **THEN** a subsequent navigation SHALL be served from the cache

#### Scenario: An uncacheable navigation falls back

- **WHEN** the network is unavailable and a navigation cannot be satisfied from
  the cache
- **THEN** the offline page SHALL be shown

### Requirement: A rebuilt static asset reaches an installed client

The service worker SHALL serve the application's stylesheets and scripts from the
network when the network is reachable, falling back to its cache when it is not.

It SHALL NOT serve a cached stylesheet or script in preference to an available
network copy. The application shell is already fetched network-first, so a
cache-first rule for the assets it loads pairs new markup with old behavior
indefinitely — and the resulting faults present as feature bugs in code that is
correct, which is the most expensive kind of report to answer.

The server SHALL NOT instruct the browser to hold those files beyond
revalidation. Their filenames carry no content hash and never will — nothing
under the web root is built or bundled, so a changed file keeps its URL. A
long-lived `max-age` therefore defeats the network-first strategy above, because
the worker's own fetch consults the HTTP cache. Neither layer is wrong on its
own, which is what makes the pair hard to see.

The service worker script itself SHALL always be revalidated. It is the code that
decides what every other response may serve, so a held copy freezes the caching
policy of the whole application at whatever it was — and withholds the upgrade
that would correct it.

The install control offered inside the Actions tray SHALL prompt for
installation, in the same way as the header's copy.

#### Scenario: An upgraded container serves upgraded assets

- **WHEN** a client that has previously loaded the app requests it again after
  the container has been rebuilt with changed stylesheets or scripts
- **THEN** the client SHALL receive the rebuilt stylesheets and scripts

#### Scenario: The app still runs offline

- **WHEN** the network is unreachable and the client has loaded the app before
- **THEN** the app SHALL load from cache, including its vendored Alpine build,
  the overlay stylesheet and the overlay script

#### Scenario: Assets are revalidated rather than held

- **WHEN** the app's stylesheets, scripts or the service worker script are
  requested
- **THEN** the response SHALL direct the browser to revalidate rather than to
  reuse the file for a fixed period

#### Scenario: Genuinely static files keep their long cache

- **WHEN** an image shipped in the image, or artwork under the data volume, is
  requested
- **THEN** it SHALL keep its long-lived cache directive

#### Scenario: A cache from a previous scheme is discarded

- **WHEN** the service worker activates after the caching scheme has changed
- **THEN** caches belonging to the previous scheme SHALL be deleted

#### Scenario: Installing from the Actions tray

- **WHEN** installation is available and the user taps the install control
  inside the Actions tray
- **THEN** the installation prompt SHALL be shown

### Requirement: An unreachable server may be answered from cache; a reachable one never is

The service worker SHALL distinguish a request that could not reach the server
from a request the server answered.

Where the fetch fails outright — no network, no route, no response — the worker
MAY answer from a copy it holds. Where the server answers, that answer SHALL be
returned as-is, whatever its status. A cached copy SHALL NOT stand in for an
error the server actually produced.

A container whose entrypoint failed answers; it does not vanish. Serving a stale
copy in that case hides a broken install behind a working-looking one, which is
the failure mode this project already spent years on.

This is invisible on a working network and only shows up on the day something is
broken, so it is stated as a requirement rather than left to the implementation.

#### Scenario: The network is gone

- **WHEN** the app requests a resource and the fetch cannot reach the server
- **THEN** the worker MAY serve a copy it holds, if it holds one and the resource
  is one that may be cached

#### Scenario: The server answers with an error

- **WHEN** the server responds with a non-success status
- **THEN** that response SHALL be returned to the app and no cached copy SHALL
  be substituted

#### Scenario: An error response is not stored

- **WHEN** the server answers with a non-success status
- **THEN** no cached copy SHALL be created or updated from it

### Requirement: The library data is never cached, in either direction

`/config.json` and the library snapshots SHALL be fetched from the container
every time. The worker SHALL NOT read them from a cache and SHALL NOT write them
to one.

**Not read**, because the app cannot tell the user whether what they are looking
at is current. An empty grid is indistinguishable from a library with no items,
and a stale grid is indistinguishable from a fresh one. The app already treats
that ambiguity as a defect elsewhere; it does not introduce it here. Where the
container cannot be reached, the app reports that and shows nothing.

**Not written**, because nothing would read it back. A cache entry that cannot be
served is live code that cannot succeed — which is exactly the defect this
change removes, and re-adding the write is how it comes back.

#### Scenario: A repeat visit still gets current data

- **WHEN** the app loads for the second or hundredth time
- **THEN** the configuration and the snapshots SHALL be fetched from the
  container, not served from a cache

#### Scenario: An unreachable container is reported

- **WHEN** the container cannot be reached
- **THEN** the app SHALL report that, and SHALL NOT present a previously held
  library as though it were current

### Requirement: Artwork and the app's own assets are cached for speed

Artwork SHALL be served stale-while-revalidate, and the app's own stylesheets and
scripts SHALL be served network-first with a cache fallback.

This is what the worker is for. Artwork is addressed by a stable path and only
re-downloaded by the fetchers when its MD5 changes, so a repeat visit paints a
grid of thousands of posters without a single round trip. The assets share the
app shell's strategy so markup and behavior cannot drift apart, while the cache
fallback keeps the interface rendering immediately.

Neither may be changed to a strategy that consults the network before painting,
and neither may be changed to one that cannot upgrade.

#### Scenario: A repeat visit costs no artwork requests

- **WHEN** the app is loaded again on a client that has loaded it before
- **THEN** the posters already held SHALL render from cache without being
  requested from the container

#### Scenario: Assets upgrade when the app does

- **WHEN** a new build changes a stylesheet or script without changing its URL
- **THEN** the client SHALL receive the new file rather than a held copy

