## ADDED Requirements

### Requirement: PRIMARY_SERVER is corrected when it names an unusable server

The entrypoint SHALL resolve `PRIMARY_SERVER` against the credentials actually
present. When it names a server that has no URL and token pair, the entrypoint
SHALL select a configured server instead, preferring Plex, then Jellyfin, then
Emby, and SHALL report the substitution on stdout.

When `PRIMARY_SERVER` is unset or names something other than `plex`, `jellyfin`,
or `emby`, the entrypoint SHALL select the first configured server in that same
order.

This behavior is long-standing and its warning text appears in support threads;
it is preserved rather than reconsidered.

#### Scenario: Named server has no credentials

- **WHEN** `PRIMARY_SERVER` is `plex`, no Plex credentials are set, and Jellyfin
  credentials are set
- **THEN** the resolved primary server SHALL be `jellyfin`, `config.json` SHALL
  carry `primaryServer` of `jellyfin`, and the entrypoint SHALL print a warning
  naming both the requested and the selected server

#### Scenario: Preference order when several alternatives exist

- **WHEN** `PRIMARY_SERVER` is `emby`, no Emby credentials are set, and both
  Plex and Jellyfin credentials are set
- **THEN** the resolved primary server SHALL be `plex`

#### Scenario: Unset primary server

- **WHEN** `PRIMARY_SERVER` is unset and only Emby credentials are set
- **THEN** the resolved primary server SHALL be `emby`

#### Scenario: Unrecognised primary server

- **WHEN** `PRIMARY_SERVER` is set to `kodi` and Plex credentials are set
- **THEN** the resolved primary server SHALL be `plex`

#### Scenario: A valid primary server is left alone

- **WHEN** `PRIMARY_SERVER` is `jellyfin` and Jellyfin credentials are set
- **THEN** the resolved primary server SHALL be `jellyfin` and no substitution
  warning SHALL be printed

### Requirement: The active server comes from the URL path

The application SHALL determine its active server from the first path segment.
When that segment names a configured server, that server SHALL be active.
Otherwise the active server SHALL be the primary server from `config.json`.

The `/plex/`, `/jellyfin/` and `/emby/` URLs are documented and bookmarkable, so
they SHALL continue to resolve.

#### Scenario: A sub-route selects its server

- **WHEN** the application is loaded from `/jellyfin/` on an install where
  Jellyfin is configured
- **THEN** the active server SHALL be Jellyfin and the grid SHALL be populated
  from `data/jellyfin`

#### Scenario: The root selects the primary server

- **WHEN** the application is loaded from `/` and `primaryServer` is `emby`
- **THEN** the active server SHALL be Emby

#### Scenario: A sub-route for an unconfigured server

- **WHEN** the application is loaded from `/emby/` on an install where Emby is
  not configured
- **THEN** the application SHALL redirect to `/`

### Requirement: The page title names the active server

The document title SHALL be the configured application title followed by the
active server's display name, separated by a space-hyphen-space. The title SHALL
carry exactly one server name regardless of how many times the page is loaded or
the server is switched.

#### Scenario: Title on the primary route

- **WHEN** `APP_TITLE` is `My Library` and the active server is Plex
- **THEN** the document title SHALL be `My Library - Plex`

#### Scenario: Title after switching servers

- **WHEN** the user switches from Plex to Jellyfin
- **THEN** the document title SHALL be `<APP_TITLE> - Jellyfin` and SHALL NOT
  contain `Plex`

#### Scenario: The title is applied to the heading too

- **WHEN** `APP_TITLE` is `My Library`
- **THEN** the application heading SHALL read `My Library`, without a server
  name

### Requirement: The server switcher matches the number of configured servers

The application SHALL present a way to change servers only when more than one is
configured. With exactly two, it SHALL present a toggle naming the other server.
With three, it SHALL present a menu listing the servers that are not active. With
one, no switching control SHALL be shown.

#### Scenario: One server configured

- **WHEN** only Plex is configured
- **THEN** no server switching control SHALL be present in the interface

#### Scenario: Two servers configured

- **WHEN** Plex and Jellyfin are configured and Plex is active
- **THEN** a toggle SHALL be shown naming Jellyfin

#### Scenario: Three servers configured

- **WHEN** Plex, Jellyfin and Emby are configured and Jellyfin is active
- **THEN** a menu SHALL be shown listing Plex and Emby, and SHALL NOT list
  Jellyfin

#### Scenario: Switching to any configured pair

- **WHEN** Plex and Emby are configured, Plex is active, and the user activates
  the toggle
- **THEN** the application SHALL navigate to Emby's route and Emby SHALL become
  the active server

### Requirement: Each server has a distinct theme applied before first paint

The application SHALL apply the active server's palette by setting a
`data-server` attribute on the document root, with the palettes declared as
custom properties in the stylesheet.

The attribute SHALL be set before first paint. Applying it after the document has
loaded shows the default palette and then replaces it — a visible flash of the
wrong brand on every load for any non-default server.

Palettes: Plex `#e5a00d` primary and `#f1b020` hover; Jellyfin `#00a4dc` and
`#0288c2`; Emby `#52c41a` and `#389e0d`.

#### Scenario: The active server's palette is applied

- **WHEN** the active server is Jellyfin
- **THEN** the document root SHALL carry `data-server="jellyfin"` and the
  resolved primary colour SHALL be `#00a4dc`

#### Scenario: No flash of the wrong palette

- **WHEN** the application is loaded with Emby active
- **THEN** the document root SHALL carry `data-server="emby"` at first paint

#### Scenario: Theming introduces no style injection

- **WHEN** the application is loaded with any server active
- **THEN** no `<style>` element SHALL be added to the document at runtime, and
  the theme SHALL be expressed entirely through custom properties

### Requirement: Server-specific icons follow the active server

The application SHALL point its icon links at the active server's icon set,
`images/<server>/` for Jellyfin and Emby and `images/` for Plex, and SHALL use
that server's logo in the header.

Icons are the one part of theming a custom property cannot express, a
`<link rel="icon">` requiring a real address.

#### Scenario: Icons for a non-default server

- **WHEN** the active server is Emby
- **THEN** the apple touch icon and both favicon links SHALL resolve under
  `images/emby/`

#### Scenario: Icons for the default server

- **WHEN** the active server is Plex
- **THEN** the icon links SHALL resolve directly under `images/`

#### Scenario: A user-supplied logo is honoured

- **WHEN** a file is mounted over `/app/web/images/logo.png` and the active
  server is Plex
- **THEN** the header SHALL display that file
