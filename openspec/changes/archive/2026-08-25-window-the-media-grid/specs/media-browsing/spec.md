## ADDED Requirements

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
