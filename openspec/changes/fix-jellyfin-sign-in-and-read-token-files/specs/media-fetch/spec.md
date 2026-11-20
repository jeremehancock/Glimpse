# Spec Delta

## ADDED Requirements

### Requirement: Each identity of the shared adapter signs in the way its server expects

The Jellyfin/Emby fetcher SHALL be told which identity it is fetching for. As
Jellyfin it SHALL send the token as `Authorization: MediaBrowser Token="<token>"`
and SHALL NOT send `X-Emby-Token`. As Emby it SHALL send `X-Emby-Token`.

Current Jellyfin rejects `X-Emby-Token`, so a Jellyfin library otherwise stops
updating while still showing its last snapshot.

#### Scenario: A Jellyfin fetch signs in with the Authorization header

- **WHEN** the fetcher runs as the Jellyfin identity with token `abc123`
- **THEN** every request it makes SHALL carry the header
  `Authorization: MediaBrowser Token="abc123"` and SHALL NOT carry
  `X-Emby-Token`

#### Scenario: An Emby fetch signs in as it always has

- **WHEN** the fetcher runs as the Emby identity with token `abc123`
- **THEN** every request it makes SHALL carry the header `X-Emby-Token: abc123`

#### Scenario: The identity is not named

- **WHEN** the fetcher is run by hand without naming an identity
- **THEN** it SHALL act as the Jellyfin identity

#### Scenario: Every scheduled and boot fetch names its identity

- **WHEN** the container installs its crontab and runs its boot fetches with
  Jellyfin and Emby both configured
- **THEN** the Jellyfin fetch SHALL name the Jellyfin identity and the Emby
  fetch SHALL name the Emby identity

### Requirement: Each identity reads its own exclusion list

When the fetcher takes its exclusion list from the environment, it SHALL read
`JELLYFIN_EXCLUDE_LIBRARIES` as the Jellyfin identity and
`EMBY_EXCLUDE_LIBRARIES` as the Emby identity, and SHALL NOT read the other
identity's variable.

#### Scenario: Both servers configured with different exclusions

- **WHEN** `JELLYFIN_EXCLUDE_LIBRARIES` is `Home Videos` and
  `EMBY_EXCLUDE_LIBRARIES` is `Private`, and the fetcher runs as Jellyfin
- **THEN** it SHALL exclude `Home Videos` and SHALL NOT exclude `Private`

#### Scenario: Only the other identity's list is set

- **WHEN** only `EMBY_EXCLUDE_LIBRARIES` is set and the fetcher runs as Jellyfin
- **THEN** it SHALL exclude no libraries
