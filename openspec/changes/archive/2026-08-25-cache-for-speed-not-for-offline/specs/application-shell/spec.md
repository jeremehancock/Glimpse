## ADDED Requirements

### Requirement: The configuration is read once, from the container, or reported

The frontend SHALL continue to read its configuration exactly once at boot, into
a single store, from `/config.json`, and SHALL report any failure to read it
rather than defaulting around it.

There is no exception for an unreachable container, and this is worth stating
because **one was built and withdrawn**. `serve-the-library-offline` retained the
last configuration the container returned, so an installed app could open away
from its network. It worked, and it was reverted: the app has no way to tell the
user whether the library they are then shown is current, and presenting one that
may be out of date is the same ambiguity this requirement exists to refuse.

Reintroducing it is a product decision, not a wiring one.

A note for whoever tries: the boot read is a **synchronous** request, and a
browser dispatches no fetch event for one. The service worker never sees it and
cannot answer it from a cache. Any retention would have to live somewhere
readable before first paint, because the theme is applied from it and applying it
later is a visible flash of the wrong brand.

#### Scenario: The container answers

- **WHEN** the container returns a valid configuration
- **THEN** the app SHALL start from it

#### Scenario: The container answers badly

- **WHEN** the container answers with an error status, or with a body that is not
  valid configuration
- **THEN** the app SHALL report the configuration as unavailable

#### Scenario: The container cannot be reached

- **WHEN** the configuration request cannot reach the container
- **THEN** the app SHALL report the configuration as unavailable, and SHALL NOT
  start from any previously held copy

#### Scenario: Configuration is still read once

- **WHEN** the app is running
- **THEN** it SHALL NOT re-read the configuration, from cache or from the
  network, and there SHALL be no second source for any setting
