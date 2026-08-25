# genre-filter Specification

## Purpose
TBD - created by archiving change convert-overlays-to-trays. Update Purpose after archive.
## Requirements
### Requirement: Genres are derived from the loaded library with counts

The application SHALL derive the genre list from the items currently loaded, per
content type, each with the number of items carrying it. The list SHALL be
ordered and SHALL include an entry selecting all genres.

Deriving from the loaded snapshot rather than from a fixed list means a genre
appears exactly when the library contains it.

#### Scenario: Genres come from the library

- **WHEN** the movies library contains items in three distinct genres
- **THEN** the genre list SHALL offer those three genres plus an all-genres entry

#### Scenario: Counts reflect the library

- **WHEN** four movies carry the genre Comedy
- **THEN** the Comedy entry SHALL show a count of four

#### Scenario: Genres are per content type

- **WHEN** the user switches from movies to TV shows
- **THEN** the genre list SHALL be derived from TV shows

#### Scenario: An empty library offers only all genres

- **WHEN** no items are loaded for the current type
- **THEN** the genre list SHALL contain only the all-genres entry

### Requirement: The genre filter is one control at every width

The genre filter SHALL be presented through a single overlay using the shared
presentation — a tray on a narrow viewport, a dialog on a wide one.

There SHALL NOT be a separate implementation per viewport. Today's desktop
dropdown and phone drawer are two implementations of one control, which is why
every genre feature has had to be built twice.

#### Scenario: One implementation serves both widths

- **WHEN** the genre filter is opened on a narrow viewport and on a wide one
- **THEN** both SHALL render from the same markup, differing only in
  presentation

#### Scenario: Opening the genre filter

- **WHEN** the user activates the genre control
- **THEN** an overlay SHALL open listing every genre with its count

#### Scenario: Choosing a genre filters and dismisses

- **WHEN** the user selects a genre
- **THEN** the overlay SHALL close and the library SHALL show only items of that
  genre

#### Scenario: The active genre is indicated

- **WHEN** a genre other than all genres is active and the filter is opened
- **THEN** that genre SHALL be shown as selected

#### Scenario: Clearing the filter

- **WHEN** the user selects the all-genres entry
- **THEN** the overlay SHALL close and every item of the current type SHALL be
  shown

### Requirement: The genre filter composes with search and sort

Filtering by genre SHALL narrow the current result set rather than replace it,
and SHALL survive a change of sort order.

#### Scenario: Genre narrows a search

- **WHEN** a search term is active and the user selects a genre
- **THEN** the library SHALL show only items matching both

#### Scenario: Genre survives a sort change

- **WHEN** a genre is active and the user changes the sort order
- **THEN** the genre SHALL remain active and the filtered items SHALL be
  reordered

#### Scenario: Switching content type resets the genre

- **WHEN** a genre is active and the user switches between movies and TV shows
- **THEN** the filter SHALL return to all genres, the previous genre not
  necessarily existing in the other type

### Requirement: Choosing a genre returns the grid to its beginning

When the user chooses a genre from the genre tray, the grid SHALL be scrolled
back to its beginning, so the filtered results are read from the top rather than
at whatever offset the user had reached under the previous filter.

The control exists only inside an overlay, so the page is pinned by the scroll
lock whenever it runs. Scrolling the window directly therefore moves nothing, and
the position is overwritten a frame later when the lock releases and restores
where the user was. The scroll SHALL be expressed as the position the page is to
settle at once the overlay has closed, not as an immediate scroll.

#### Scenario: The grid returns to the top after choosing a genre

- **WHEN** the user has scrolled down the grid, opens the genre tray, and
  chooses a genre
- **THEN** the tray SHALL close and the grid SHALL be positioned at its
  beginning

#### Scenario: The previous position is not restored

- **WHEN** the genre tray closes because a genre was chosen
- **THEN** the page SHALL NOT return to the offset it held when the tray opened

### Requirement: A genre is presented as a tappable choice, not as raw button chrome

Each entry in the genre tray SHALL carry its own background, border and radius,
sized so the whole entry is a comfortable touch target.

It SHALL NOT rely on the browser's default button appearance. The entry is a
`<button>` carrying two `<span>`s, and the rule that styles it was written for
full-width `<div>` rows in a dropdown that no longer exists — so with no
presentation of its own it renders as the user agent's own control: a white box
with a system border, laid out inline and wrapping raggedly.

The entries SHALL wrap within the tray's width, and none SHALL overflow it
horizontally.

The entry representing the active genre SHALL be visually distinct from the
others, and SHALL carry that state in the accessibility tree as well as in its
appearance — a class alone is invisible to a screen reader.

#### Scenario: An entry is presented as a control

- **WHEN** the genre tray is opened
- **THEN** each entry SHALL draw its own background, border and radius rather
  than the browser's default button appearance

#### Scenario: Entries wrap inside the tray

- **WHEN** the genre tray is opened at any supported width
- **THEN** the entries SHALL wrap within the tray and none SHALL extend beyond
  its horizontal bounds

#### Scenario: The active genre is marked

- **WHEN** a genre other than the default is in force and the tray is opened
- **THEN** that entry SHALL be visually distinct and SHALL expose its selected
  state to assistive technology

### Requirement: A genre's count is secondary to its name

Where an entry shows how many items a genre holds, the count SHALL be separated
from the name and SHALL be presented as secondary information — quieter than the
name it qualifies.

The two SHALL NOT run together. With neither element styled, `Action` and `794`
abut as `Action794`, which reads as one word and makes the name unrecognisable at
a glance.

An entry whose count is zero or unknown SHALL show no count rather than a zero.

#### Scenario: Name and count are distinguishable

- **WHEN** an entry with a count is shown
- **THEN** the count SHALL be visually separated from the name and rendered
  less prominently

#### Scenario: No count is shown when there is none

- **WHEN** an entry has no count
- **THEN** no count element SHALL be visible for it

