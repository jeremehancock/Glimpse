## ADDED Requirements

### Requirement: The grid shows the container's current snapshot or says it could not load it

The grid SHALL render from the snapshot the container returns for this request.
It SHALL NOT render from a previously held copy.

The snapshot is already a point-in-time copy written on a cron schedule, so the
grid is never live to the second. That is a known and bounded staleness the user
can reason about — "as of the last fetch". A cached copy is not: it is stale by
an unknown amount, for an unknown reason, with nothing on screen to say so.

Where the snapshot cannot be fetched, the app SHALL say the library could not be
loaded. An empty grid SHALL NOT be shown in its place — an empty library and an
unreachable one are indistinguishable on screen, and the app already treats that
ambiguity as a defect.

The artwork those snapshots point at is exempt and is served from cache wherever
it is held. A poster is only rewritten when its MD5 changes, so the held copy is
almost always the current one, and serving it is what lets a grid of thousands
paint without a round trip.

#### Scenario: The grid reflects the current snapshot

- **WHEN** the app loads and the container is reachable
- **THEN** the grid SHALL render the snapshot the container just returned

#### Scenario: An unfetchable snapshot is not an empty library

- **WHEN** the snapshot cannot be fetched
- **THEN** the app SHALL say the library could not be loaded, and SHALL NOT
  present an empty grid as though the library had no items

#### Scenario: Artwork still comes from cache

- **WHEN** the grid renders and the posters it references are already held
- **THEN** those posters SHALL be served from cache rather than re-requested
