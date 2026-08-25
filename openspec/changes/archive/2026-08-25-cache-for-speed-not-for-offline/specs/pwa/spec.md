## ADDED Requirements

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
