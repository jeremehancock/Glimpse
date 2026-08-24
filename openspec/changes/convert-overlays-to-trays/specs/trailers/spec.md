## ADDED Requirements

### Requirement: A trailer plays in a dialog sized to the video

Activating an item's trailer control SHALL open an overlay containing the
trailer, presented as a centred dialog at every width — a trailer is sized to its
video's aspect ratio rather than to the screen, which is what the tray shape
exists to fill.

The overlay SHALL indicate that the trailer is loading until it can play.

#### Scenario: Opening a trailer

- **WHEN** the user activates the trailer control for an item that has one
- **THEN** an overlay SHALL open containing that item's trailer

#### Scenario: Centred at every width

- **WHEN** a trailer is opened on a narrow viewport
- **THEN** the overlay SHALL be centred rather than docked to the bottom edge

#### Scenario: Loading is indicated

- **WHEN** a trailer overlay is opened and the video has not yet loaded
- **THEN** a loading indication SHALL be shown

### Requirement: Closing a trailer stops playback

Dismissing the trailer overlay SHALL stop the trailer playing. Audio continuing
after the overlay has gone is the failure this prevents.

#### Scenario: Dismissing stops the video

- **WHEN** a trailer is playing and the user dismisses the overlay
- **THEN** playback SHALL stop and no audio SHALL continue

#### Scenario: Dismissed by Escape

- **WHEN** a trailer overlay is open and the user presses Escape
- **THEN** it SHALL close and playback SHALL stop

#### Scenario: Dismissed by the backdrop

- **WHEN** the user activates the area outside a trailer overlay's panel
- **THEN** it SHALL close and playback SHALL stop

### Requirement: A trailer opened from the detail overlay returns to it

The trailer overlay SHALL be openable from the detail overlay, and dismissing it
SHALL leave the detail overlay open beneath.

The control that opens it SHALL move focus before its own overlay changes state,
so that dismissing the trailer returns a keyboard user to the detail overlay
rather than to the top of the page.

#### Scenario: The detail overlay survives the trailer

- **WHEN** a trailer is opened from the detail overlay and then dismissed
- **THEN** the detail overlay SHALL still be open

#### Scenario: Focus returns to the detail overlay

- **WHEN** a keyboard user opens a trailer from the detail overlay and dismisses
  it
- **THEN** focus SHALL return to a control within the detail overlay
