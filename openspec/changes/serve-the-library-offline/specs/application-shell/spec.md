## ADDED Requirements

### Requirement: An unreachable configuration may be answered from the last one received

The frontend SHALL continue to read its configuration exactly once at boot, into
a single store, from `/config.json`.

Where that request cannot reach the container, the client MAY be served the last
configuration this container returned to it, and the app SHALL start from it.

This is a narrow exception and its boundaries are the requirement:

- It applies ONLY when the request fails to reach the server. A configuration
  the server actually returned — including an error status, an empty body, or
  malformed JSON — SHALL be reported, never replaced by a cached copy.
- The cached copy SHALL be one this client received from this container. It is
  not a default, a built-in, or a value inferred from the environment. Nothing is
  invented.
- A client with no cached copy SHALL report the configuration as unavailable,
  exactly as today.
- The retained copy SHALL be readable before first paint, because the theme is
  applied from it and applying it later is a visible flash of the wrong brand.
  This rules out the service worker's cache: the boot read is a synchronous
  request, for which no fetch event is dispatched, so the worker never sees it.
  The page retains its own copy for that reason and no other.

The distinction matters because the failure this rule guards against is a
misconfigured install that looks like a working one. A container that answers
with an error is present and broken, and the user needs to see that. A container
that cannot be reached is a different situation entirely: the app is being opened
away from the network it belongs to, and the last known configuration is a fact
about that container rather than a guess.

#### Scenario: Offline boot uses the last configuration

- **WHEN** the app boots, the container cannot be reached, and a configuration
  from a previous successful boot is held
- **THEN** the app SHALL start using that configuration

#### Scenario: A failed entrypoint is still reported

- **WHEN** the container answers the configuration request with an error status
- **THEN** the app SHALL report the configuration as unavailable, even if a
  cached copy is held

#### Scenario: Malformed configuration is still reported

- **WHEN** the container answers with a body that is not valid configuration
- **THEN** the app SHALL report it, even if a cached copy is held

#### Scenario: A first boot with no network reports

- **WHEN** the app boots with no network and no cached configuration
- **THEN** the app SHALL report the configuration as unavailable

#### Scenario: Configuration is still read once

- **WHEN** the app is running
- **THEN** it SHALL NOT re-read the configuration, from cache or from the
  network, and there SHALL be no second source for any setting
