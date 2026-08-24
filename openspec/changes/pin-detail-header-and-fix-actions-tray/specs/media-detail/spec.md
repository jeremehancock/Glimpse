## ADDED Requirements

### Requirement: The detail overlay keeps the item's identity in view while it scrolls

The detail overlay SHALL divide its panel into a region that stays fixed and a
region that scrolls. The item's poster, year, content rating, duration and
trailer control SHALL be in the fixed region. The summary, genres, cast and date
added SHALL be in the scrolling region.

The division SHALL be the same at every viewport width. The overlay changes shape
between a tray and a dialog, but which parts of it hold still is a property of
the content, not of the viewport.

The fixed region SHALL NOT grow so tall that the scrolling region is unusable on
a short viewport.

#### Scenario: The poster stays put while the summary scrolls

- **WHEN** the user scrolls the detail overlay's content on a phone
- **THEN** the poster, year, rating and duration SHALL remain visible in place
- **AND** the summary, genres, cast and date added SHALL move

#### Scenario: The same division on a pointer device

- **WHEN** the detail overlay is opened as a centred dialog and its content is
  scrolled
- **THEN** the poster, year, rating and duration SHALL remain visible in place

#### Scenario: A long title does not consume the panel

- **WHEN** the detail overlay is opened for an item whose title wraps to several
  lines on a short viewport
- **THEN** the scrolling region SHALL still be present and scrollable

#### Scenario: The trailer control is always reachable

- **WHEN** the detail overlay is opened for an item that has a trailer and the
  user has scrolled to the end of the content
- **THEN** the trailer control SHALL still be visible without scrolling back

### Requirement: The item's backdrop artwork is confined to the fixed region

The item's backdrop artwork SHALL extend no further down the panel than the fixed
region does, so that scrolling content never passes over or under it.

The artwork SHALL NOT obscure the grab handle. Where the artwork reaches the top
edge of the panel it SHALL be faded out behind the handle so the handle stays
legible against it.

#### Scenario: Artwork does not reach the scrolling content

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL end where the fixed region ends
- **AND** no scrolling content SHALL move across it

#### Scenario: The grab handle stays legible

- **WHEN** the detail overlay is opened as a tray for an item with backdrop
  artwork
- **THEN** the grab handle SHALL be distinguishable from the artwork behind it

#### Scenario: No artwork is not a gap

- **WHEN** the detail overlay is opened for an item with no backdrop artwork
- **THEN** the fixed region SHALL render normally against the panel's own surface
