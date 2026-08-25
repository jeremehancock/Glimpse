# roulette Specification

## Purpose
TBD - created by archiving change convert-overlays-to-trays. Update Purpose after archive.
## Requirements
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

### Requirement: The roulette is a tray on touch and a dialog on a pointer device

The roulette overlay SHALL present as a bottom tray below the touch breakpoint
and as a centred dialog above it, like the detail overlay.

It is the last overlay still centred at every width. On a phone that leaves one
overlay arriving from the middle of the screen while every other one rises from
the bottom edge, which reads as an oversight rather than as a distinction.

To present as a tray it SHALL carry the three regions the overlay system
requires: a grab handle, a head, and a body. It has none of them today — it is a
panel wrapping a spinner — so this is structural rather than a modifier class.
Adding the modifier alone would produce a tray with nothing to drag and, because
the modifier hides the close button on touch, no way to dismiss it.

The drag region and the scrolling region SHALL remain separate elements, as for
every other overlay.

#### Scenario: A tray on a phone

- **WHEN** the roulette is opened below the touch breakpoint
- **THEN** it SHALL be docked to the bottom edge, span the full width, and show
  its grab handle

#### Scenario: A dialog on a desktop

- **WHEN** the roulette is opened above the touch breakpoint
- **THEN** it SHALL be centred and SHALL show its close button

#### Scenario: It can be dismissed on touch

- **WHEN** the roulette is open on a phone and the user drags its handle
  downward past the dismissal threshold
- **THEN** the overlay SHALL close

### Requirement: The roulette names itself and can be closed

The roulette overlay SHALL carry a visible title, and SHALL offer a close control
at every width — the close button on a pointer device, the grab handle on touch.

Today it offers neither outside its error state: while it is choosing there is no
close control at all, and dismissing by backdrop is deliberately suppressed. An
overlay that cannot be dismissed while it works is tolerable only while the work
is brief, and it stops being tolerable the moment anything hangs.

Suppressing backdrop dismissal while it is choosing SHALL remain. A stray tap
cancelling a pick the user just asked for reads as the control not working; that
reasoning is unchanged and is why the affordances above are explicit ones.

#### Scenario: The overlay is named

- **WHEN** the roulette is opened
- **THEN** a visible title SHALL identify it, and the overlay SHALL expose that
  name to assistive technology

#### Scenario: It can be closed while choosing

- **WHEN** the roulette is choosing and the user activates its close affordance
- **THEN** the overlay SHALL close

#### Scenario: The backdrop still does not dismiss it

- **WHEN** the roulette is choosing and the user taps the backdrop
- **THEN** the overlay SHALL remain open

