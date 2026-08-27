## RENAMED Requirements

- FROM: `### Requirement: A trailer plays in a dialog sized to the video`
- TO: `### Requirement: A trailer plays in an overlay sized to the video`

## MODIFIED Requirements

### Requirement: A trailer plays in an overlay sized to the video

Activating an item's trailer control SHALL open an overlay containing the
trailer.

The overlay SHALL be presented as a tray on touch viewports and as a centred
dialog on pointer viewports, following the same presentation rule as every other
overlay in the app. On a phone the tray is full width and the video fills that
width exactly, so the concern that produced the earlier centred-everywhere
exception — a 16:9 frame letterboxed inside a panel wider than itself — does not
arise at that width.

The overlay SHALL indicate that the trailer is loading until it can play.

The video SHALL be bounded by the height available to it as well as by the width,
so that a short viewport does not push the video past the panel that holds it.

#### Scenario: Opening a trailer

- **WHEN** the user activates the trailer control for an item that has one
- **THEN** an overlay SHALL open containing that item's trailer

#### Scenario: A tray on a phone

- **WHEN** a trailer is opened on a touch viewport
- **THEN** the overlay SHALL be docked to the bottom edge and SHALL carry a grab
  handle as its dismissal affordance

#### Scenario: A dialog on a desktop

- **WHEN** a trailer is opened on a pointer viewport
- **THEN** the overlay SHALL be centred and SHALL offer a close control

#### Scenario: Loading is indicated

- **WHEN** a trailer overlay is opened and the video has not yet loaded
- **THEN** a loading indication SHALL be shown

#### Scenario: A short viewport does not overflow the panel

- **WHEN** a trailer is opened on a viewport too short to hold a full-width 16:9
  video
- **THEN** the video SHALL be reduced to fit within the panel rather than
  extending past it

## ADDED Requirements

### Requirement: The trailer overlay names the item it is playing

The trailer overlay's title SHALL identify the item whose trailer is playing,
rather than being a constant label. The panel SHALL be labelled by that title so
that assistive technology announces the item on open.

A title too long for the head SHALL be truncated rather than allowed to grow the
head. The head is part of the drag region on touch, and a head that grows with
its content is a drag region whose height depends on which item was opened.

When the overlay is dismissed, the title SHALL be reset along with the rest of
the overlay's state, so that the next open cannot briefly show the previous
item's name.

#### Scenario: The head names the item

- **WHEN** the trailer overlay is opened for an item
- **THEN** its title SHALL contain that item's title

#### Scenario: Assistive technology announces the item

- **WHEN** the trailer overlay receives focus
- **THEN** its accessible name SHALL be derived from that title rather than from
  a constant label

#### Scenario: A long title does not grow the head

- **WHEN** the trailer overlay is opened for an item whose title is longer than
  the head can show
- **THEN** the title SHALL be truncated and the head SHALL keep the height it has
  for a short title

#### Scenario: A dismissed trailer does not leak its title into the next one

- **WHEN** a trailer overlay is dismissed and another is opened for a different
  item
- **THEN** the title shown SHALL be the newly opened item's

### Requirement: The trailer overlay is drawn from the shared surface tokens

The trailer overlay's panel, head and border SHALL be drawn from the same design
tokens as every other overlay. It SHALL NOT declare its own panel background.

Only the well that holds the video SHALL be black. Black is correct there because
a video letterboxes against its own container and letterboxing against any other
colour reads as a rendering fault — it is a property of the media, not a theme
choice, and it SHALL NOT extend to the panel around it.

The loading indication SHALL be drawn on that same black well, opaque rather than
as a translucent wash over it, so that the region holding the video does not
change colour when the video arrives.

The loading indication's spinner SHALL take its colours from the design tokens,
including the per-server accent, rather than hardcoding them.

#### Scenario: The panel matches the app's other overlays

- **WHEN** the trailer overlay is open
- **THEN** its panel SHALL use the shared overlay surface, border and radius, and
  SHALL NOT use a panel background declared only for this overlay

#### Scenario: The well behind the video is black

- **WHEN** a trailer is playing in an aspect ratio that does not fill the well
- **THEN** the area around the video SHALL be black

#### Scenario: The loading state does not change the panel's colour

- **WHEN** a trailer overlay moves from loading to playing
- **THEN** the region holding the video SHALL be the same colour before and after

#### Scenario: The spinner follows the server's accent

- **WHEN** the trailer overlay is opened while a server whose accent differs from
  another's is selected
- **THEN** the spinner SHALL be drawn in that server's accent colour
