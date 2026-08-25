## ADDED Requirements

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
