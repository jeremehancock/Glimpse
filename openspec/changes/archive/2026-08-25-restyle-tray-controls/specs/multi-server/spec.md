## ADDED Requirements

### Requirement: A server destination is presented like any other tray choice

Each destination in the server switcher SHALL carry the same presentation as an
entry in the genre tray: its own background, border and radius, sized as a touch
target, wrapping within the overlay.

The two share a class deliberately — they are the same control offering different
things — so a change to one SHALL apply to the other. Styling them apart is how
they drift, and this switcher inherited its current appearance precisely because
it reuses a class that lost its rules.

A destination SHALL show no count. The genre entry's count element is optional,
and a server has nothing to count.

#### Scenario: Destinations are presented as controls

- **WHEN** three or more servers are configured and the switcher is opened
- **THEN** each destination SHALL draw its own background, border and radius
  rather than the browser's default button appearance

#### Scenario: A destination shows no count

- **WHEN** the server switcher is opened
- **THEN** no destination SHALL display a count
