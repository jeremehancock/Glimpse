## ADDED Requirements

### Requirement: Roulette picks a random item from what is currently shown

The application SHALL offer a control that selects one item at random and opens
its detail overlay.

The selection SHALL be drawn from the items currently displayed — honouring the
active content type, search term and genre filter — not from the whole library. A
user who has filtered to Comedy is asking for a random comedy.

#### Scenario: A random item is chosen and opened

- **WHEN** the user activates the roulette control
- **THEN** one item SHALL be selected at random and its detail overlay SHALL open

#### Scenario: The active filters are respected

- **WHEN** a genre filter is active and the user activates the roulette control
- **THEN** the selected item SHALL carry that genre

#### Scenario: The active search is respected

- **WHEN** a search term is active and the user activates the roulette control
- **THEN** the selected item SHALL be one of the search results

#### Scenario: The content type is respected

- **WHEN** the TV shows tab is active and the user activates the roulette control
- **THEN** the selected item SHALL be a TV show

### Requirement: Roulette runs in a dialog that reports having nothing to pick

While selecting, the application SHALL show an overlay indicating that a choice
is being made, presented as a centred dialog at every width.

When no item can be selected because nothing matches the current filters, the
overlay SHALL say so and offer a way to dismiss it. It MUST NOT close silently,
which is indistinguishable from the control not working.

#### Scenario: Selection is indicated

- **WHEN** the user activates the roulette control
- **THEN** an overlay SHALL indicate that a selection is being made

#### Scenario: Nothing to choose from

- **WHEN** the user activates the roulette control and no items match the current
  filters
- **THEN** the overlay SHALL report that there is nothing to select and offer a
  dismissal control

#### Scenario: The overlay gives way to the detail view

- **WHEN** an item has been selected
- **THEN** the roulette overlay SHALL close and the item's detail overlay SHALL
  open

### Requirement: Dismissing a roulette result returns to the library

The detail overlay opened by roulette SHALL be dismissible in the usual ways, and
dismissing it SHALL return to the library rather than to the roulette overlay.

#### Scenario: Dismissing returns to the library

- **WHEN** the detail overlay opened by roulette is dismissed
- **THEN** the library SHALL be shown and no overlay SHALL remain open
