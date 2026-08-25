## ADDED Requirements

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
