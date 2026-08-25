## ADDED Requirements

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
