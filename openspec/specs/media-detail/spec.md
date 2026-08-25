# media-detail Specification

## Purpose
TBD - created by archiving change convert-overlays-to-trays. Update Purpose after archive.
## Requirements
### Requirement: The detail overlay shows an item's full metadata

Selecting an item in the library SHALL open an overlay showing that item's
poster, title, year, content rating, duration, summary, genres, cast, and the
date it was added, over the item's backdrop image where one exists.

A field the snapshot does not carry SHALL be omitted rather than shown empty.

#### Scenario: Opening an item

- **WHEN** the user selects a movie in the grid
- **THEN** an overlay SHALL open showing that movie's poster, title, year,
  rating, duration, summary, genres, cast and date added

#### Scenario: A missing field is omitted

- **WHEN** an item has no content rating in the snapshot
- **THEN** the overlay SHALL NOT display an empty rating

#### Scenario: A missing backdrop is not an error

- **WHEN** an item has no backdrop image
- **THEN** the overlay SHALL open and render its content without one

#### Scenario: TV shows open the same way

- **WHEN** the user selects a TV show
- **THEN** the overlay SHALL open with that show's metadata

### Requirement: The detail overlay is a tray on touch and a dialog on a pointer device

The detail overlay SHALL use the shared overlay presentation: docked to the
bottom edge on a narrow viewport, centred on a wide one.

A centred box on a phone puts its close control in a top corner, which is the
hardest part of the screen to reach one-handed and the reason the tray shape
exists.

#### Scenario: Presented as a tray on a phone

- **WHEN** the detail overlay is opened on a narrow viewport
- **THEN** it SHALL be docked to the bottom edge with a grab handle

#### Scenario: Dismissed by swiping down

- **WHEN** the user drags the detail overlay's handle downward past the threshold
- **THEN** it SHALL close

#### Scenario: Dismissed by the backdrop

- **WHEN** the user activates the area outside the detail overlay's panel
- **THEN** it SHALL close

#### Scenario: Dismissed by Escape

- **WHEN** the detail overlay is open and the user presses Escape
- **THEN** it SHALL close

### Requirement: The detail overlay offers a trailer when the item has one

When an item's metadata carries a trailer, the detail overlay SHALL offer a
control to watch it. When it does not, no such control SHALL be shown.

#### Scenario: An item with a trailer

- **WHEN** the detail overlay is opened for an item whose metadata names a
  trailer
- **THEN** a control to watch the trailer SHALL be shown

#### Scenario: An item without a trailer

- **WHEN** the detail overlay is opened for an item with no trailer
- **THEN** no trailer control SHALL be shown

### Requirement: Selecting a genre in the detail overlay filters the library

Genres shown in the detail overlay SHALL be selectable, and choosing one SHALL
dismiss the overlay and filter the library to that genre.

#### Scenario: Choosing a genre filters and dismisses

- **WHEN** the user selects a genre inside the detail overlay
- **THEN** the overlay SHALL close and the library SHALL show only items of that
  genre

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

### Requirement: The grab handle stays legible over any item's artwork

The detail overlay's grab handle SHALL be drawn above the item's backdrop
artwork, and the artwork SHALL be fully transparent across the whole area the
handle occupies.

Both halves are required. The artwork is positioned and the handle is not, so
paint order alone puts the artwork on top whatever its opacity; and lifting the
handle without clearing the artwork behind it leaves a grey bar over an arbitrary
photograph, whose legibility then depends on which item was opened.

The distance over which the artwork clears SHALL be derived from the handle's
own metrics rather than restated, and SHALL extend past the handle's lower edge
rather than ending at it.

The artwork SHALL still reach the panel's top edge — the full-bleed appearance is
deliberate, and moving the artwork down instead would leave a band of bare
surface reading as a gap.

#### Scenario: The handle is not covered by artwork

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the grab handle SHALL be drawn above that artwork

#### Scenario: The artwork is clear behind the handle

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL be fully transparent over the handle and for a
  margin below its lower edge

#### Scenario: The artwork still reaches the top edge

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL fill the fixed region to the panel's top edge, with
  no band of bare surface above it

### Requirement: Nothing is drawn between the item's title and its artwork

The detail overlay SHALL NOT draw a divider beneath the item's title.

The title sits in the fixed region, over the item's backdrop artwork. A hairline
there crosses the picture rather than separating two surfaces, and it is the
first thing the eye lands on.

The division between the fixed region and the scrolling region SHALL remain
drawn. That border is doing real work — it is where the poster and metadata stop
holding still and the summary begins to move — and it sits at the foot of the
identity block, on surface rather than on artwork.

#### Scenario: No divider under the title

- **WHEN** the detail overlay is opened
- **THEN** no divider SHALL be drawn between the title and the item's poster
  block

#### Scenario: The region division survives

- **WHEN** the detail overlay is opened
- **THEN** the boundary between the fixed region and the scrolling region SHALL
  remain visible

