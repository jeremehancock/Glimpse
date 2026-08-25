# sorting Specification

## Purpose
TBD - created by archiving change fix-overlay-layering-and-dead-tray-controls. Update Purpose after archive.
## Requirements
### Requirement: The sort controls apply the sort at every width they are offered

Where the sort controls are presented inside an overlay because the header is too
narrow to hold them, activating one SHALL re-sort the grid, mark itself as the
active sort, and dismiss the overlay — the same outcome as activating the
header's copy at a wider viewport.

Dismissing the overlay SHALL NOT be the whole of the control's behavior.

The grid SHALL return to the top when the sort method changes, so the user sees
the new ordering from its beginning rather than at whatever offset they had
scrolled to under the old one. This SHALL hold whichever copy of the control was
activated.

Where the control was activated from inside an overlay, the page is pinned by the
scroll lock, so scrolling the window directly moves nothing and is overwritten
when the lock releases. The scroll SHALL be expressed as the position the page is
to settle at once the overlay has closed.

#### Scenario: Sorting from the Actions tray re-sorts the grid

- **WHEN** the user taps a sort control inside the Actions tray
- **THEN** the grid SHALL be re-sorted by that method and the tray SHALL close

#### Scenario: The active sort is reflected in the tray

- **WHEN** the user opens the Actions tray
- **THEN** the control matching the sort currently in force SHALL be marked
  active and the other SHALL NOT

#### Scenario: Changing sort returns to the top of the grid

- **WHEN** the sort method changes from a scrolled position
- **THEN** the grid SHALL be scrolled back to its beginning

