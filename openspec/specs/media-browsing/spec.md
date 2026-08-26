# media-browsing Specification

## Purpose
TBD - created by archiving change cache-for-speed-not-for-offline. Update Purpose after archive.
## Requirements
### Requirement: The grid shows the container's current snapshot or says it could not load it

The grid SHALL render from the snapshot the container returns for this request.
It SHALL NOT render from a previously held copy.

The snapshot is already a point-in-time copy written on a cron schedule, so the
grid is never live to the second. That is a known and bounded staleness the user
can reason about — "as of the last fetch". A cached copy is not: it is stale by
an unknown amount, for an unknown reason, with nothing on screen to say so.

Where the snapshot cannot be fetched, the app SHALL say the library could not be
loaded. An empty grid SHALL NOT be shown in its place — an empty library and an
unreachable one are indistinguishable on screen, and the app already treats that
ambiguity as a defect.

The artwork those snapshots point at is exempt and is served from cache wherever
it is held. A poster is only rewritten when its MD5 changes, so the held copy is
almost always the current one, and serving it is what lets a grid of thousands
paint without a round trip.

#### Scenario: The grid reflects the current snapshot

- **WHEN** the app loads and the container is reachable
- **THEN** the grid SHALL render the snapshot the container just returned

#### Scenario: An unfetchable snapshot is not an empty library

- **WHEN** the snapshot cannot be fetched
- **THEN** the app SHALL say the library could not be loaded, and SHALL NOT
  present an empty grid as though the library had no items

#### Scenario: Artwork still comes from cache

- **WHEN** the grid renders and the posters it references are already held
- **THEN** those posters SHALL be served from cache rather than re-requested

### Requirement: The grid's DOM cost does not grow with the library

The number of item elements in the document SHALL be bounded by what the viewer
can reach, not by the number of items in the library.

A library is data; a grid is a rendering of part of it. Rendering every item as
an element ties the browser's per-frame style, layout and paint cost to how much
media the user owns, so the application gets slower for exactly the people who
use it most. At 7,000 items this is not a degradation — the page runs at ~3fps
while idle, with nothing animating, and every animation elsewhere in the
application inherits that. The overlay trays were reported as "choppy" for this
reason and there is nothing wrong with the trays.

The bound SHALL hold regardless of the active tab, the search term, the genre
filter or the sort order, because each of those changes which items are rendered
and none of them changes how many can be seen at once.

#### Scenario: A large library renders a bounded number of elements

- **WHEN** a library of several thousand items is browsed
- **THEN** the number of item elements in the document SHALL remain bounded and
  SHALL NOT be proportional to the number of items in the library

#### Scenario: The bound survives filtering and sorting

- **WHEN** the search term, genre filter, sort order or tab changes
- **THEN** the number of item elements SHALL remain within the same bound

#### Scenario: Interaction stays responsive at library scale

- **WHEN** an overlay is opened while a large library is displayed
- **THEN** the page SHALL continue to produce animation frames at a rate that
  renders the overlay's transition as motion rather than as a jump

### Requirement: Every item remains reachable by scrolling

Bounding the rendered elements SHALL NOT bound what the viewer can browse.

The grid SHALL extend as the viewer scrolls toward its end, so that continuing
to scroll continues to reveal items until the last item of the current selection
has been shown. There SHALL be no page controls, no "load more" affordance and
no numbered pages — the change is to how the grid is rendered, not to how it is
navigated.

The document's scrollable extent SHALL be consistent with what has been
rendered, so that the scroll position the viewer is holding does not move under
them as the grid extends.

#### Scenario: Scrolling reaches the last item

- **WHEN** the viewer scrolls continuously to the end of a large library
- **THEN** the final item of the current selection SHALL be reachable and
  rendered

#### Scenario: Extending the grid does not move the viewer

- **WHEN** the grid extends because the viewer scrolled toward its end
- **THEN** the content already on screen SHALL remain at the same position

#### Scenario: No pagination controls are introduced

- **WHEN** the grid is displayed at any library size
- **THEN** no page number, page size or "load more" control SHALL be presented

### Requirement: An item's entrance animation is not scheduled from its position in the library

An item's entrance delay SHALL be derived from its position within what is
currently being rendered, and SHALL be capped.

Deriving it from the item's index in the whole library multiplies a per-item
delay by a number the application does not control. At a 30ms step the 100th
item waits three seconds and the 7,000th waits **209.97 seconds**; measured,
6,611 of 7,000 items sat at `opacity: 0` twenty-five seconds after load. The
grid was not slow to animate — most of it was invisible, and scrolling into it
showed empty space where cards were.

An entrance animation exists to soften an arrival the viewer is watching. A
delay longer than the viewer's attention is not a softer arrival; it is a
missing item.

#### Scenario: No item waits longer than the cap

- **WHEN** any number of items is rendered
- **THEN** no item's entrance delay SHALL exceed the cap, whatever its position
  in the library

#### Scenario: Items rendered later still animate in

- **WHEN** the grid extends and renders further items
- **THEN** those items SHALL animate in on the same terms as the first ones

#### Scenario: Every rendered item becomes visible

- **WHEN** the grid has been displayed and its entrance animations have run
- **THEN** every rendered item SHALL be fully opaque

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

