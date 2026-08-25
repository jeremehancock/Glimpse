## ADDED Requirements

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
