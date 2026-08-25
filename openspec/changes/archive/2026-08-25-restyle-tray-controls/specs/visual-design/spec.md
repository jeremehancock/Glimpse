## ADDED Requirements

### Requirement: A tray offers one way to close on touch

Below the touch breakpoint, an overlay presenting as a tray SHALL offer the grab
handle as its dismissal affordance and SHALL NOT also show a close button.

Two dismissals, one of which is a small target in the corner furthest from a
thumb, is worse than one that is obvious. `.modal--tray-on-touch` already hides
its close button for this reason; a `.sheet` is a tray at that width by
definition and SHALL do the same.

Above the breakpoint, where a tray presents as a centred dialog and the handle is
hidden because there is no drag to make, the close button SHALL be shown. An
overlay SHALL never present with neither affordance.

#### Scenario: A tray shows a handle and no close button

- **WHEN** a tray is opened below the touch breakpoint
- **THEN** its grab handle SHALL be visible and its close button SHALL NOT be

#### Scenario: A dialog shows a close button and no handle

- **WHEN** the same overlay is opened above the touch breakpoint
- **THEN** its close button SHALL be visible and its grab handle SHALL NOT be

#### Scenario: Every overlay keeps an affordance at every width

- **WHEN** any overlay is opened at any width
- **THEN** at least one of its grab handle or its close button SHALL be visible

### Requirement: A head divider is not drawn across artwork

Where an overlay's head sits over the item's artwork rather than over a flat
surface, it SHALL NOT draw a divider beneath itself.

A hairline that separates two bands of surface reads as structure; the same
hairline crossing a photograph reads as a seam, and the eye finds it before it
finds the title.

Where the head sits on a flat surface the divider SHALL remain. This is a rule
about what the divider crosses, not a decision that the divider was wrong.

#### Scenario: No divider over artwork

- **WHEN** the detail overlay is opened for an item with backdrop artwork
- **THEN** no divider SHALL be drawn beneath its title

#### Scenario: The divider survives elsewhere

- **WHEN** an overlay whose head sits on a flat surface is opened
- **THEN** the divider beneath its title SHALL be drawn
