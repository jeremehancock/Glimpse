## MODIFIED Requirements

### Requirement: A tray on touch, a dialog on a pointer device

The media detail overlay, the menu, the server switcher, the genre filter and the
trailer SHALL be presented as a tray on narrow, touch-first viewports and as a
centred dialog on wide viewports. The roulette overlay SHALL be presented this
way too, being a status overlay rather than a screenful of content.

There is no longer an overlay that is a dialog at every width. The trailer was
the exception, on the reasoning that a trailer is sized to its video and a tray's
job is to fill the width of a screen — but at touch widths a tray IS the width of
the screen, and a full-width 16:9 video fills it exactly. The reasoning described
a desktop and was applied at every width.

An overlay whose content has a fixed aspect ratio SHALL be bounded by the height
available to it as well as by the width, so that a short viewport reduces the
content to fit rather than pushing it past the panel.

#### Scenario: Detail view on a phone

- **WHEN** the media detail overlay is opened on a narrow viewport
- **THEN** it SHALL be docked to the bottom edge and SHALL slide up from it

#### Scenario: Detail view on a desktop

- **WHEN** the media detail overlay is opened on a wide viewport
- **THEN** it SHALL be centred in the viewport

#### Scenario: The trailer is a tray on a phone

- **WHEN** the trailer overlay is opened on a narrow viewport
- **THEN** it SHALL be docked to the bottom edge rather than centred

#### Scenario: The trailer is a dialog on a desktop

- **WHEN** the trailer overlay is opened on a wide viewport
- **THEN** it SHALL be centred in the viewport

#### Scenario: Fixed-ratio content fits a short viewport

- **WHEN** an overlay holding fixed-ratio content is opened on a viewport too
  short to show that content at full width
- **THEN** the content SHALL be reduced to fit within the panel

#### Scenario: The grab handle is a touch affordance only

- **WHEN** an overlay is presented as a centred dialog on a pointer device
- **THEN** the grab handle SHALL NOT be shown, and the overlay SHALL offer a
  close control instead

## ADDED Requirements

### Requirement: An overlay holding media draws its panel from the shared tokens

An overlay SHALL NOT declare its own panel background, border or radius. The
panel is the app's surface wherever it appears; an overlay that paints its own is
an overlay that stops matching the app the first time a token changes, silently.

An overlay holding media MAY paint the WELL that the media sits in black, and
only that well. Black there is a property of the medium — video letterboxes
against its container, and letterboxing against any colour but black reads as a
rendering fault — not a theme decision, so it SHALL be scoped to the well and
SHALL NOT extend to the panel, the head or the border.

A placeholder shown in that well while the media loads SHALL be drawn on the same
colour as the well, opaque rather than translucent over it. A translucent
placeholder composites to a different colour than the well beneath it, so the
overlay visibly changes colour at the moment the media arrives — which is exactly
when the viewer is looking at it.

#### Scenario: The panel is the app's surface

- **WHEN** any overlay is open
- **THEN** its panel SHALL use the shared overlay surface, border and radius
  tokens rather than values declared for that overlay alone

#### Scenario: A media well may be black

- **WHEN** an overlay holds a video
- **THEN** the region containing that video MAY be black while the panel around
  it remains the shared surface

#### Scenario: A loading placeholder does not shift the well's colour

- **WHEN** an overlay's media finishes loading and replaces its placeholder
- **THEN** the well SHALL be the same colour before and after
