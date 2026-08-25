## ADDED Requirements

### Requirement: A committed swipe moves the grid in the direction of the gesture

When a swipe commits to a tab change, the outgoing grid SHALL leave the screen
in the direction of the swipe and the incoming grid SHALL arrive from the
opposite edge.

A swipe that succeeded and a swipe that fell short of the threshold currently
produce the same first frame: the screen either changes or it does not, with
nothing in between connecting the gesture to its result. The application
compensates with a toast that names the tab a moment later, which is a caption
for a transition that never happened.

The motion is the confirmation. It also states which direction the viewer
travelled, which the toast does not — after two swipes it is the difference
between knowing where you are and reading a label.

#### Scenario: The outgoing tab leaves toward the swipe

- **WHEN** a swipe commits to a tab change
- **THEN** the outgoing tab SHALL move off the screen in the direction the
  finger travelled, and the incoming tab SHALL move in from the opposite edge

#### Scenario: A swipe that does not commit does not move the grid

- **WHEN** a touch gesture fails the distance or angle test for a tab change
- **THEN** the grid SHALL NOT move, and the active tab SHALL be unchanged

#### Scenario: Reduced motion is honoured

- **WHEN** the viewer has asked for reduced motion
- **THEN** the tab change SHALL complete without a sustained animation, and the
  incoming tab SHALL still be correctly rendered and active

### Requirement: No part of an incoming tab is visible before it has been rendered

The incoming tab SHALL be fully rendered, with its loading indicator resolved,
before any part of it is on screen.

Until this change nothing in the application had ever shown an inactive tab. A
tab is rendered only when it becomes active, and the tab that has never been
active still holds an empty grid and a loading spinner from first paint — the
spinner is hidden only for the tab being rendered. A transition that reveals
the incoming tab before its render lands therefore does not show blank rows on
the first switch; it shows a spinner, and on later switches it shows whatever
that tab was displaying under a filter that may since have changed.

#### Scenario: The first switch to a tab shows no loading state

- **WHEN** a tab is switched to for the first time since load
- **THEN** its loading indicator SHALL NOT be visible at any point during the
  transition

#### Scenario: The incoming tab arrives showing its own top

- **WHEN** the transition begins
- **THEN** the incoming tab SHALL already be showing the first items of its
  current search, genre and sort selection

#### Scenario: A tab rendered while inactive uses the correct selection

- **WHEN** a tab is rendered before it has been made active
- **THEN** it SHALL be rendered against that tab's data with the search term,
  genre filter and sort order that will apply once it is active

### Requirement: The scroll reset is not a separate visible motion

A tab change resets the viewer to the top of the incoming tab. That reset SHALL
NOT be perceivable as motion distinct from the tab change itself.

Both tabs scroll as one document, so the two grids cannot hold different scroll
offsets while both are on screen. Resetting before the transition makes the
page jump to the top and then slide — two movements for one gesture, and the
jump is the one the viewer notices. Resetting after it leaves the incoming tab
arriving at an offset it will immediately abandon.

#### Scenario: No jump precedes or follows the transition

- **WHEN** a swipe commits while the viewer is scrolled well down a tab
- **THEN** the viewer SHALL see one continuous movement, with no scroll jump
  before it begins or after it ends

#### Scenario: The viewer lands at the top of the incoming tab

- **WHEN** the transition completes
- **THEN** the page SHALL be at the top of the incoming tab

#### Scenario: An open overlay's scroll lock is respected

- **WHEN** a tab change occurs while an overlay holds the scroll lock
- **THEN** the scroll reset SHALL be applied through the overlay system rather
  than directly, so the position the overlay restores on close is the new one

### Requirement: The transition is gated by the same condition as the gesture

The tab transition SHALL be enabled by the same condition that binds the swipe
gesture, and SHALL NOT be keyed to a separate breakpoint or media query.

Two conditions describing one capability drift. This project has already paid
for that: the rule hiding a page control and the rule showing the overlay
trigger that replaced it were written as separate media queries, reached 992px
and 768px independently, and left every width between them with neither.

Stating it once means a width can never exist where the gesture fires and the
animation does not, or the reverse.

#### Scenario: Pointer tab switching is unchanged

- **WHEN** a tab is switched by clicking a tab control
- **THEN** the change SHALL be immediate, with no transition

#### Scenario: Every width that swipes also animates

- **WHEN** the swipe gesture is active at a given viewport
- **THEN** the transition SHALL be active at that same viewport, and at no
  viewport where the gesture is inactive

### Requirement: A tab change completes correctly regardless of the transition

The active tab, its rendered contents and the state of the surrounding controls
SHALL be correct once a tab change is requested, whether or not the transition
runs, completes, or is interrupted by another tab change.

An animation is presentation. Making the resulting state depend on it — on a
`transitionend` that a hidden tab never fires, on a timer, or on a second swipe
arriving mid-flight — turns a visual detail into a correctness one, and the
failure is a tab that is active but shows the wrong library.

#### Scenario: A second swipe during a transition resolves to one tab

- **WHEN** a swipe commits while a previous transition is still running
- **THEN** exactly one tab SHALL end active, showing its own contents, with no
  element left displaced or hidden by the interrupted transition

#### Scenario: The genre and sort controls follow the new tab

- **WHEN** a tab change completes
- **THEN** the genre selection SHALL be reconciled against the new tab's
  genres and the surrounding controls SHALL describe the new tab, exactly as
  they do for a pointer tab switch

#### Scenario: No element remains displaced after the transition

- **WHEN** the transition has ended
- **THEN** neither tab SHALL retain a transform, a fixed position or an
  imposed height from the transition, and the document SHALL scroll normally
