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

