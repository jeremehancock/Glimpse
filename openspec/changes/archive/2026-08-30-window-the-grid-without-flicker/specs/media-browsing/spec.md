## ADDED Requirements

### Requirement: Extending the window does not rebuild what is already on screen

Moving the rendered window SHALL NOT return an item that is already displayed to
a loading state.

A viewer scrolling through a grid is looking at the items it is showing them.
Rebuilding the elements that hold those items — even into identical markup —
discards each poster's loaded image and starts it again from its placeholder, so
the images the viewer is currently reading blink out and fade back in. It happens
on the way back up as readily as on the way down, over posters that finished
loading seconds earlier, which is what distinguishes it from a slow network.

The window SHALL therefore be re-anchored on the viewer's approach to its edge
rather than on every row they cross. A window holding sixty rows that re-anchors
every row rebuilds the whole of what it is showing in order to change under two
percent of what it holds.

The rendered window SHALL carry comparable unrendered runway in both scroll
directions. Runway placed only below the viewer leaves upward scrolling with
nothing pre-rendered to absorb it, so the direction with the least margin is the
one most likely to be scrolling back over already-loaded artwork.

An item's artwork that has already loaded SHALL be presented as loaded when its
element is rebuilt, without a placeholder and without replaying its entrance
fade.

#### Scenario: Scrolling within the window changes nothing

- **WHEN** the viewer scrolls while remaining clear of the rendered window's
  edges
- **THEN** the elements holding the items on screen SHALL NOT be rebuilt

#### Scenario: Already-loaded artwork does not return to a placeholder

- **WHEN** the window is re-anchored while items whose artwork has already
  loaded are on screen
- **THEN** that artwork SHALL remain continuously displayed, and SHALL NOT show
  a loading placeholder or replay its fade

#### Scenario: Scrolling back over visited items is stable

- **WHEN** the viewer scrolls back up through items they have already scrolled
  past
- **THEN** those items' artwork SHALL be displayed without reloading

#### Scenario: Both directions carry runway

- **WHEN** the viewer scrolls upward from within a large library
- **THEN** items SHALL be rendered ahead of them in that direction on the same
  terms as when scrolling downward

### Requirement: The grid's geometry is only recorded from a laid-out grid

Row pitch and column count SHALL be recorded only from a grid that has been laid
out, and a measurement taken from a grid that has not SHALL NOT be stored.

A hidden grid answers questions about its geometry with zeros rather than with an
error. An element that is not rendered has no height, so a card measured through
one reports a row pitch of zero — a number that reads as a successfully measured
grid whose rows have no height. Every consequence of that follows silently:
window arithmetic divides by it, spacer heights compute to negative lengths that
the browser discards as invalid, and the document ends after the first window
with the rest of the library beyond any scroll.

This is reached on the ordinary path rather than an exceptional one. An incoming
tab is required to be fully rendered before any part of it is visible, so it is
rendered while it is still hidden; measuring it at that moment is measuring a
grid that has no layout.

An unmeasured grid SHALL refuse to render a window rather than render one from
placeholder geometry, and SHALL be measured once it is laid out. "Not yet
measured" and "windowing is not required here" SHALL be distinguishable, so that
a grid which was never measurable cannot present as one that was.

#### Scenario: A hidden grid is not measured

- **WHEN** a grid is rendered while it is not displayed
- **THEN** no row pitch or column count taken from it SHALL be retained

#### Scenario: A tab measures itself once it is shown

- **WHEN** a tab that was rendered while hidden becomes the displayed tab
- **THEN** its geometry SHALL be measured from its laid-out grid before its
  window is next moved

#### Scenario: A failed measurement is not mistaken for a working one

- **WHEN** the grid's geometry has not been successfully measured
- **THEN** the grid SHALL NOT present a window computed from that geometry, and
  the condition SHALL be distinguishable from a grid that needs no window

#### Scenario: A resize is not the only repair

- **WHEN** a tab is browsed after being reached without the viewport ever
  changing size
- **THEN** its grid SHALL behave identically to one reached after a resize

## MODIFIED Requirements

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

This SHALL hold however the tab was reached. Where a tab can only be reached by
a gesture — the tab controls are hidden at phone widths, so the swipe is the
only way into the other tab there — that gesture is not an edge case but the
sole entrance, and a grid that extends only for tabs reached some other way does
not extend at all for the viewers who own that device.

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

#### Scenario: A tab first shown by the swipe gesture extends

- **WHEN** a tab holding more items than one window is reached by the swipe
  gesture and scrolled to its end
- **THEN** its final item SHALL be reachable, without the viewport having been
  resized or the device rotated
