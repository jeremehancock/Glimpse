## REMOVED Requirements

### Requirement: A committed swipe moves the grid in the direction of the gesture

**Reason**: The gesture is now the transition rather than something a transition
plays back after it, and one of this requirement's scenarios has become false
rather than merely reworded. "A swipe that does not commit does not move the
grid" was the correct guarantee for a discrete gesture evaluated once at
`touchend`. Under a drag the grid moves for the whole gesture and returns to
rest on release, which is the entire point of the change — so keeping the
requirement and editing around that scenario would leave a scenario name
asserting the opposite of the behaviour it documents.

**Migration**: Replaced in full by "A tab drag moves both grids with the finger"
below. The two guarantees that survive are carried into it verbatim in
substance: the outgoing tab leaves toward the swipe with the incoming arriving
from the opposite edge (now "A committed drag completes the travel"), and
reduced motion is honoured (unchanged in name and intent). Nothing that was
required of a committed swipe stops being required of a committed drag.

## ADDED Requirements

### Requirement: A tab drag moves both grids with the finger

A horizontal touch drag on the grid SHALL move the tabs with the finger. The
outgoing tab SHALL track the touch, and the incoming tab SHALL enter from the
opposite edge at the same rate, one viewport apart, both updating for as long as
the touch continues.

The two tabs SHALL NOT overlap at any point in the gesture. One leaves as the
other arrives; neither is ever drawn over the other.

On release the gesture SHALL resolve to exactly one of three outcomes: it
commits and the tabs complete their travel, it is abandoned and the tabs return
to rest with the active tab unchanged, or it was never claimed and nothing
moved.

A swipe that succeeded and a swipe that fell short used to produce the same
first frame: nothing moved until the finger left the glass, so the viewer could
not see that the gesture was working, could not see how far was left, and could
not change their mind. The motion is the confirmation, and it has to happen
while the thumb is still down to be one.

Overlapping them was tried and reverted. An incoming tab entering at a fraction
of the outgoing tab's speed — the familiar platform parallax — necessarily sits
on top of it for the whole gesture, and which of the two is drawn above the
other is then decided by their order in the document rather than by the
direction of travel. The result was one tab appearing to win every time,
whichever way the thumb went.

#### Scenario: The tabs follow the finger

- **WHEN** a horizontal drag is in progress
- **THEN** the outgoing tab's horizontal offset SHALL correspond to the
  distance the touch has travelled, updating as the touch moves

#### Scenario: The incoming tab arrives as the outgoing one leaves

- **WHEN** a horizontal drag is in progress
- **THEN** the incoming tab SHALL be visible entering from the opposite edge at
  the same rate the outgoing tab leaves, and SHALL arrive at rest at the same
  moment the outgoing tab completes its travel

#### Scenario: Neither tab is ever drawn over the other

- **WHEN** a horizontal drag is in progress, in either direction
- **THEN** the two tabs SHALL remain one viewport apart and SHALL NOT overlap,
  so which tab is visible depends only on how far the drag has travelled

#### Scenario: Reversing the drag reverses the tabs

- **WHEN** the touch reverses direction mid-drag
- **THEN** the tabs SHALL follow it back, and a drag that returns to its origin
  SHALL leave the tabs at rest

#### Scenario: A committed drag completes the travel

- **WHEN** a drag is released having travelled at least a third of the viewport
  width, or at a speed above the flick threshold
- **THEN** the outgoing tab SHALL continue off the screen in the direction the
  finger travelled, the incoming tab SHALL complete its entry, and the tab
  change SHALL take effect

#### Scenario: An abandoned drag restores the previous tab

- **WHEN** a drag is released having travelled less than the commit distance
  and below the flick threshold
- **THEN** both tabs SHALL return to rest, the active tab SHALL be unchanged,
  and the viewer SHALL be returned to the scroll position they were at when the
  drag began

#### Scenario: A drag past the threshold can still be abandoned

- **WHEN** a drag travels past the commit distance and is then dragged back
  below it before release
- **THEN** the gesture SHALL be abandoned rather than committed

#### Scenario: The settle is timed from the distance still to travel

- **WHEN** a drag is released
- **THEN** the tabs SHALL complete their movement over a duration proportional
  to the distance remaining, bounded below by a floor and above by the tab
  transition duration

#### Scenario: Reduced motion is honoured

- **WHEN** the viewer has asked for reduced motion
- **THEN** the tabs SHALL still follow the finger, because the viewer is moving
  them directly
- **AND** the settle after release SHALL be effectively instant, with the
  incoming tab correctly rendered and active

### Requirement: The gesture's axis is decided once, early, and held

A touch on the grid SHALL be assigned to exactly one axis within the first few
pixels of travel, and that assignment SHALL hold for the remainder of the
touch.

A touch assigned to the vertical axis SHALL be left entirely to the browser's
scrolling for the rest of its life. A touch assigned to the horizontal axis
SHALL have the browser's default handling suppressed from that point on.

The application previously claimed a horizontal gesture only after 100px of
travel. That is too late for a drag in two independent ways: nothing can move
until the gesture is claimed, and a touch sequence whose early moves were not
cancelled has in some browsers already been given to the scroller, where later
attempts to cancel it are ignored. The 100px figure is not lost — it belongs to
the commit test, which is what it was always measuring.

A gesture that re-arbitrates its axis mid-drag can hand a moving page back to
the scroller halfway through, so it SHALL NOT.

#### Scenario: A vertical drag scrolls and is never claimed

- **WHEN** a touch's initial travel is predominantly vertical
- **THEN** the page SHALL scroll normally, the tabs SHALL NOT move, and the
  touch SHALL NOT be claimed later in its life however it subsequently moves

#### Scenario: A horizontal drag is claimed before the page can scroll

- **WHEN** a touch's initial travel is predominantly horizontal
- **THEN** the gesture SHALL be claimed within the first few pixels of travel,
  and the page SHALL NOT scroll for the remainder of that touch

#### Scenario: A tap is neither

- **WHEN** a touch begins and ends without exceeding the axis-lock distance
- **THEN** no tab drag SHALL have begun, and the touch SHALL behave exactly as
  it does today

### Requirement: A drag with nowhere to go resists

A horizontal drag toward a tab that does not exist SHALL move the current tab
by a damped fraction of the touch's travel and SHALL return it to rest on
release, without changing the active tab.

Movies is the first tab and TV Shows is the last. A drag off either end
currently does nothing at all, which is indistinguishable from a gesture the
application failed to recognise. Resistance says there is nothing there, which
is the fact the viewer is missing.

#### Scenario: Dragging past the first tab resists

- **WHEN** the viewer drags rightward while Movies is active
- **THEN** the Movies tab SHALL move by a damped fraction of the travel, no
  incoming tab SHALL appear, and it SHALL return to rest on release

#### Scenario: Dragging past the last tab resists

- **WHEN** the viewer drags leftward while TV Shows is active
- **THEN** the TV Shows tab SHALL move by a damped fraction of the travel, no
  incoming tab SHALL appear, and it SHALL return to rest on release

#### Scenario: A resisted drag never commits

- **WHEN** a resisted drag is released at any distance or speed
- **THEN** the active tab SHALL be unchanged

### Requirement: The grid's rendered window does not move while the tabs do

While a tab drag is live, the application SHALL NOT recompute which rows either
grid renders.

The window is derived from the grid's measured position on screen. The drag
applies a scale to the moving tab as part of its lift, which changes that
measurement for every card in it — so a window computed during the drag would
be computed against a position the viewer never occupied, and would present as
an off-by-one in the grid rather than as a transform problem.

This SHALL be an explicit refusal in the code that recomputes the window. It
SHALL NOT rest on the incidental fact that a frozen tab cannot receive scroll
events: a safety that is implied by a mechanism rather than stated is a safety
that disappears when the mechanism changes, and this project has already
shipped a pair of rules that were meant to be one condition and drifted apart.

#### Scenario: No re-window during a drag

- **WHEN** a tab drag is in progress
- **THEN** the rows rendered by either grid SHALL NOT change

#### Scenario: Windowing resumes after the gesture

- **WHEN** a drag has resolved, whether committed, abandoned or cancelled
- **THEN** the grid SHALL recompute its window normally on the next scroll

#### Scenario: The sliding transform stays horizontal

- **WHEN** the tabs are moved by a drag or a settle
- **THEN** the offset that moves them SHALL be horizontal, with no vertical
  component

### Requirement: An incoming tab is re-rendered unless it is provably current

Before a tab is shown, the application MAY skip re-rendering it only when
everything determining what its grid displays — the tab, the search term, the
genre filter, the sort order and the underlying data — is unchanged since it was
last rendered. In every other case it SHALL be re-rendered.

The comparison SHALL err toward re-rendering. Any input to what the grid shows
that is not covered by the comparison SHALL be treated as a change.

A tab keeps whatever it last rendered, so re-rendering one that already shows
the right thing produces identical nodes at full cost. That cost is not
incidental to this change: a drag moves it from the dead air after a finger
lifts onto the first frame of a gesture the viewer is driving.

The asymmetry is the point. Wrongly deciding a tab is stale costs a render
nobody needed. Wrongly deciding it is current shows the viewer a grid that does
not match their search, sort or genre — a wrong library that looks like a
working one, which is this application's oldest and quietest failure.

The application SHALL additionally keep the inactive tab current in the
background when the selection changes, so that the common case is a tab that is
already correct rather than one that has to be rebuilt while a thumb waits.

#### Scenario: An unchanged tab is not rebuilt

- **WHEN** a tab is shown and nothing determining its contents has changed since
  it last rendered
- **THEN** its grid SHALL NOT be rebuilt, and it SHALL display what it already
  held

#### Scenario: A changed search invalidates the other tab

- **WHEN** the viewer changes the search term, genre or sort order, and then
  moves to the other tab
- **THEN** that tab SHALL display results matching the new selection, never the
  previous one

#### Scenario: The inactive tab is kept current in the background

- **WHEN** the selection changes while one tab is active
- **THEN** the inactive tab SHALL be brought up to date without the viewer
  waiting for it, and SHALL NOT be visible while it is

#### Scenario: An unrendered tab is always rendered

- **WHEN** a tab that has never been rendered is shown
- **THEN** it SHALL be rendered before any part of it is visible

### Requirement: A drag is refused before it is claimed when an overlay is open

A touch SHALL NOT begin a tab drag while any overlay is open, or when the touch
begins inside an overlay panel or on its backdrop.

The refusal SHALL happen when the touch begins, not when it ends. A discrete
gesture could check at the end because nothing had moved; a drag that discovers
the conflict later has already suppressed the browser's handling and taken both
tabs out of the scroller.

A touch inside an overlay belongs to that overlay — its own dismissal drag, a
scroll in its body, or a backdrop tap — and never to the tabs behind it.

#### Scenario: An open overlay refuses the drag

- **WHEN** a touch begins on the page while any overlay is open
- **THEN** no tab drag SHALL begin, and the tabs SHALL NOT move

#### Scenario: A touch inside an overlay reaches the overlay

- **WHEN** a touch begins inside an overlay's panel
- **THEN** that overlay's own gesture handling SHALL apply and no tab drag
  SHALL begin

### Requirement: An interrupted drag leaves nothing pinned

A tab drag SHALL be resolved to a correct resting state when it is interrupted
by anything: a cancelled touch, a viewport resize, a tab change from another
control, or a second drag beginning.

Resolution SHALL run from a single routine that is safe to invoke repeatedly and
that clears everything the gesture set — both tabs' pinning and transforms, the
lift, the scrim, the horizontal containment, the window refusal, and any pending
frame callback.

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
