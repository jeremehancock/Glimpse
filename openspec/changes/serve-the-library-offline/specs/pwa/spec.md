## ADDED Requirements

### Requirement: An unreachable server is answered from cache; a reachable one is not

The service worker SHALL distinguish a request that could not reach the server
from a request the server answered.

Where the fetch fails outright — no network, no route, no response — the worker
MAY answer from the last copy it received. Where the server answers, that answer
SHALL be returned as-is, whatever its status. A cached copy SHALL NOT stand in
for an error the server actually produced.

This distinction is the whole of the change and it is not a detail. A container
whose entrypoint failed answers; it does not vanish. Serving a stale copy in that
case would hide a broken install behind a working-looking one — which is the
failure mode this project already spent years on, arrived at from a new
direction.

#### Scenario: The network is gone

- **WHEN** the app requests a resource and the fetch cannot reach the server
- **THEN** the worker SHALL serve the last copy it holds, if it holds one

#### Scenario: The server answers with an error

- **WHEN** the server responds with a non-success status
- **THEN** that response SHALL be returned to the app and no cached copy SHALL
  be substituted

#### Scenario: The server answers normally

- **WHEN** the server responds successfully
- **THEN** that response SHALL be returned and SHALL replace the cached copy

### Requirement: What the app needs to start is cached

The service worker SHALL cache the generated configuration and the library
snapshots as it receives them, so a client that has loaded successfully at least
once can start again with no network.

Precaching the shell, the stylesheets and the vendored script is not sufficient
and never was. Those get the app as far as reading its configuration, which is
where it stops: it has no configuration, correctly declines to invent one, and
reports an error. Every offline affordance in the project — the manifest, the
install control, the vendored Alpine, the offline page — is worth nothing while
the first thing the app reads is unavailable.

A cached copy SHALL be written only from a successful response.

#### Scenario: The app starts with no network

- **WHEN** a client that has previously loaded the app opens it with the network
  unreachable
- **THEN** the app SHALL start, read its configuration from cache, and render the
  library from the cached snapshot

#### Scenario: A never-loaded client has nothing to fall back to

- **WHEN** a client that has never successfully loaded the app opens it with the
  network unreachable
- **THEN** the offline fallback page SHALL be shown

#### Scenario: An error response is not cached

- **WHEN** the server answers with a non-success status
- **THEN** no cached copy SHALL be created or updated from it

### Requirement: A cached start is not silently equivalent to a live one

Where the app has started from cached data, it SHALL make that visible to the
user for as long as it remains true, and SHALL stop saying so once it has
reached the server again.

A library that is quietly out of date is the same class of failure as a library
that is quietly wrong: the user cannot tell a stale grid from a current one, and
will read a missing recent addition as the fetcher being broken.

#### Scenario: An offline start is announced

- **WHEN** the app has started from cached configuration or a cached snapshot
- **THEN** an indication SHALL be visible that the data is not live

#### Scenario: The indication clears

- **WHEN** the app subsequently reaches the server successfully
- **THEN** that indication SHALL be removed
