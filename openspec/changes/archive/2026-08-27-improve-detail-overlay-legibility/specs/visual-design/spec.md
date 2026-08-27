## ADDED Requirements

### Requirement: The grab handle carries its own contrast

The grab handle SHALL be drawn in a colour that holds a contrast ratio of at
least 3:1 against every surface it can appear over.

That set is two things, and both are required:

- an overlay's own panel surface, which is every tray in the app; and
- the detail overlay's backdrop artwork at its brightest, composited over that
  same panel surface.

3:1 rather than 4.5:1 because the handle is a control, not text — but it is the
control that dismisses a tray, and on touch it is the only one, so it is the last
affordance in the app that should be left to chance.

The handle SHALL be one colour for every tray. It is one component: an overlay
that dresses its own copy differently is the drift this design system exists to
prevent, and the difference would not be noticed, because two trays are rarely on
screen at once.

The handle SHALL NOT depend on what is behind it being cleared, faded or masked
away in order to meet this bar. An arrangement of that kind is made by whichever
overlay owns the thing behind the handle, so it holds for that overlay and is
simply absent everywhere else — which is how the handle came to be below 3:1
against plain panel surface for the whole of the app while being carefully
protected in the one place someone had looked.

#### Scenario: The handle is legible on a plain tray

- **WHEN** any tray is opened on a touch viewport
- **THEN** its grab handle SHALL hold at least 3:1 against the panel surface
  behind it

#### Scenario: The handle is legible over artwork

- **WHEN** the detail overlay is opened as a tray for an item whose backdrop
  artwork is fully white behind the handle
- **THEN** the handle SHALL hold at least 3:1 against that artwork as composited
  over the panel surface

#### Scenario: Every tray wears the same handle

- **WHEN** two different trays are opened
- **THEN** their grab handles SHALL be drawn in the same colour
