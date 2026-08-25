## ADDED Requirements

### Requirement: A control relocated into an overlay stays reachable at every width

Where a control is presented in the page at one viewport width and inside an
overlay at another, the width at which the page copy is withdrawn SHALL be the
width at which the overlay's trigger appears. There SHALL be no width at which
both are hidden.

A rule that hides the page copy SHALL be scoped to that copy alone. Overlay
content SHALL NOT be hidden by a rule written for the page, even where the two
share a class.

This is the failure that empties an overlay: a selector meaning "the header's
control" also matches the overlay's control, and the overlay opens with nothing
in it. Nothing errors, and the overlay's own frame renders correctly.

#### Scenario: No width hides both copies

- **WHEN** the viewport is set to any width
- **THEN** either the page's sort, genre and server controls SHALL be visible, or
  the trigger that opens the overlay carrying them SHALL be visible

#### Scenario: The Actions tray is not empty

- **WHEN** the user opens the Actions tray on a phone
- **THEN** it SHALL offer the sort, genre filter and server switch controls

#### Scenario: A page-scoped hide rule does not reach an overlay

- **WHEN** a rule hides a control that appears in the page header
- **THEN** a control of the same class inside an overlay SHALL remain visible

### Requirement: A pinned region of an overlay is part of its drag region

Where an overlay holds content fixed above its scrolling region, a downward drag
beginning on that fixed content SHALL dismiss the overlay, in the same way as a
drag beginning on the grab handle or the title bar.

The fixed region SHALL be a sibling of the scrolling region and never an ancestor
of it, so the browser does not reclaim the drag as a scroll.

A tap on a control inside the fixed region SHALL still activate that control.

#### Scenario: Dragging the pinned content dismisses

- **WHEN** the user drags downward from the fixed region of an overlay past the
  dismissal threshold
- **THEN** the overlay SHALL close

#### Scenario: A tap is not a drag

- **WHEN** the user taps a control inside an overlay's fixed region without
  moving
- **THEN** that control SHALL activate and the overlay SHALL NOT close

#### Scenario: The scrolling region still scrolls

- **WHEN** the user drags downward from the scrolling region of an overlay
- **THEN** that region SHALL scroll and the overlay SHALL NOT move
