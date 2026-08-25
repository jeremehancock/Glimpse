## ADDED Requirements

### Requirement: The grid renders from the last snapshot when the server is unreachable

Where the library snapshot cannot be fetched because the container cannot be
reached, the grid SHALL render from the last snapshot this client received.

The snapshot is already a point-in-time copy — the fetchers write it on a cron
schedule, so what the grid shows is never live in the first place. Serving
yesterday's copy of a file that is itself yesterday's copy is a much smaller step
than it appears, and it is the difference between an installed app that opens and
one that shows an error.

An empty grid SHALL NOT be shown in place of a snapshot that could not be
fetched. An empty library and an unreachable one are indistinguishable on screen,
and the app already treats that ambiguity as a defect elsewhere.

Artwork SHALL continue to be served from cache where it is held, so a cached
snapshot renders with its posters rather than as a grid of gaps.

#### Scenario: The grid renders offline

- **WHEN** the app is opened with the container unreachable and a snapshot from a
  previous session is held
- **THEN** the grid SHALL render that snapshot, with cached artwork

#### Scenario: An unreachable snapshot is not an empty library

- **WHEN** the snapshot cannot be fetched and none is held
- **THEN** the app SHALL say the library could not be loaded, and SHALL NOT
  present an empty grid as though the library had no items

#### Scenario: Search and filtering work against the cached snapshot

- **WHEN** the grid has rendered from a cached snapshot
- **THEN** search, sorting and the genre filter SHALL operate over it as they do
  over a freshly fetched one
