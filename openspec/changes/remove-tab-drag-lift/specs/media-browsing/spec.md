## MODIFIED Requirements

### Requirement: The grid's rendered window does not move while the tabs do

While a tab drag is live, the application SHALL NOT recompute which rows either
grid renders.

The window is derived from the grid's measured position on screen. A tab in a
drag is pinned out of the scroller at a captured offset, so its measured position
during the gesture is not the position the viewer is scrolled to — a window
computed from it would be computed against a position the viewer never occupied,
and would present as an off-by-one in the grid rather than as a transform
problem.

This SHALL be an explicit refusal in the code that recomputes the window. It
SHALL NOT rest on the incidental fact that a frozen tab cannot receive scroll
events: a safety that is implied by a mechanism rather than stated is a safety
that disappears when the mechanism changes, and this project has already shipped
a pair of rules that were meant to be one condition and drifted apart.

That this refusal no longer has a scale to protect against does not weaken it.
It was written when the drag scaled the moving tabs, and the scale is gone; the
refusal stands on the freeze alone and SHALL remain stated in its own right.

#### Scenario: No re-window during a drag

- **WHEN** a tab drag is in progress
- **THEN** the rows rendered by either grid SHALL NOT change

#### Scenario: Windowing resumes after the gesture

- **WHEN** a drag has resolved, whether committed, abandoned or cancelled
- **THEN** the grid SHALL recompute its window normally on the next scroll

#### Scenario: The sliding transform stays horizontal

- **WHEN** the tabs are moved by a drag or a settle
- **THEN** the offset that moves them SHALL be horizontal, with no vertical
  component and no scale

#### Scenario: The transform has no exception

- **WHEN** the transform applied to a tab during a drag, a settle or a
  transition is inspected
- **THEN** it SHALL consist of a horizontal translation and nothing else

### Requirement: An interrupted drag leaves nothing pinned

A tab drag SHALL be resolved to a correct resting state when it is interrupted
by anything: a cancelled touch, a viewport resize, a tab change from another
control, or a second drag beginning.

Resolution SHALL run from a single routine that is safe to invoke repeatedly and
that clears everything the gesture set — both tabs' pinning and transforms, the
horizontal containment, the window refusal, and any pending frame callback.

A drag takes two tabs out of the document's scroller and stops the grid
re-windowing. Leaving that in place because a touch was cancelled by an incoming
call gives the viewer a page that cannot scroll and a grid that cannot render
new rows, with nothing on screen to explain it.

#### Scenario: A cancelled touch resolves the drag

- **WHEN** a touch driving a tab drag is cancelled by the system
- **THEN** the drag SHALL resolve to a resting state, the page SHALL scroll
  normally, and the grid SHALL re-window normally

#### Scenario: A second gesture resolves the first

- **WHEN** a new tab drag begins while a settle from a previous one is still
  running
- **THEN** the previous one SHALL be fully resolved before the new one begins

#### Scenario: A resize during a drag resolves it

- **WHEN** the viewport is resized while a tab drag is in progress
- **THEN** the drag SHALL resolve to a resting state and the grid SHALL
  re-measure its layout
