# media-detail Specification

## Purpose
TBD - created by archiving change convert-overlays-to-trays. Update Purpose after archive.
## Requirements
### Requirement: The detail overlay shows an item's full metadata

Selecting an item in the library SHALL open an overlay showing that item's
poster, title, year, content rating, duration, summary, genres, cast, and the
date it was added, over the item's backdrop image where one exists.

A field the snapshot does not carry SHALL be omitted rather than shown empty.

#### Scenario: Opening an item

- **WHEN** the user selects a movie in the grid
- **THEN** an overlay SHALL open showing that movie's poster, title, year,
  rating, duration, summary, genres, cast and date added

#### Scenario: A missing field is omitted

- **WHEN** an item has no content rating in the snapshot
- **THEN** the overlay SHALL NOT display an empty rating

#### Scenario: A missing backdrop is not an error

- **WHEN** an item has no backdrop image
- **THEN** the overlay SHALL open and render its content without one

#### Scenario: TV shows open the same way

- **WHEN** the user selects a TV show
- **THEN** the overlay SHALL open with that show's metadata

### Requirement: The detail overlay is a tray on touch and a dialog on a pointer device

The detail overlay SHALL use the shared overlay presentation: docked to the
bottom edge on a narrow viewport, centred on a wide one.

A centred box on a phone puts its close control in a top corner, which is the
hardest part of the screen to reach one-handed and the reason the tray shape
exists.

#### Scenario: Presented as a tray on a phone

- **WHEN** the detail overlay is opened on a narrow viewport
- **THEN** it SHALL be docked to the bottom edge with a grab handle

#### Scenario: Dismissed by swiping down

- **WHEN** the user drags the detail overlay's handle downward past the threshold
- **THEN** it SHALL close

#### Scenario: Dismissed by the backdrop

- **WHEN** the user activates the area outside the detail overlay's panel
- **THEN** it SHALL close

#### Scenario: Dismissed by Escape

- **WHEN** the detail overlay is open and the user presses Escape
- **THEN** it SHALL close

### Requirement: The detail overlay offers a trailer when the item has one

When an item's metadata carries a trailer, the detail overlay SHALL offer a
control to watch it. When it does not, no such control SHALL be shown.

#### Scenario: An item with a trailer

- **WHEN** the detail overlay is opened for an item whose metadata names a
  trailer
- **THEN** a control to watch the trailer SHALL be shown

#### Scenario: An item without a trailer

- **WHEN** the detail overlay is opened for an item with no trailer
- **THEN** no trailer control SHALL be shown

### Requirement: Selecting a genre in the detail overlay filters the library

Genres shown in the detail overlay SHALL be selectable, and choosing one SHALL
dismiss the overlay and filter the library to that genre.

#### Scenario: Choosing a genre filters and dismisses

- **WHEN** the user selects a genre inside the detail overlay
- **THEN** the overlay SHALL close and the library SHALL show only items of that
  genre

### Requirement: The detail overlay keeps the item's identity in view while it scrolls

The detail overlay SHALL divide its panel into a region that stays fixed and a
region that scrolls. The item's poster, year, content rating, duration and
trailer control SHALL be in the fixed region. The summary, genres, cast and date
added SHALL be in the scrolling region.

The division SHALL be the same at every viewport width. The overlay changes shape
between a tray and a dialog, but which parts of it hold still is a property of
the content, not of the viewport.

The fixed region SHALL NOT grow so tall that the scrolling region is unusable on
a short viewport.

#### Scenario: The poster stays put while the summary scrolls

- **WHEN** the user scrolls the detail overlay's content on a phone
- **THEN** the poster, year, rating and duration SHALL remain visible in place
- **AND** the summary, genres, cast and date added SHALL move

#### Scenario: The same division on a pointer device

- **WHEN** the detail overlay is opened as a centred dialog and its content is
  scrolled
- **THEN** the poster, year, rating and duration SHALL remain visible in place

#### Scenario: A long title does not consume the panel

- **WHEN** the detail overlay is opened for an item whose title wraps to several
  lines on a short viewport
- **THEN** the scrolling region SHALL still be present and scrollable

#### Scenario: The trailer control is always reachable

- **WHEN** the detail overlay is opened for an item that has a trailer and the
  user has scrolled to the end of the content
- **THEN** the trailer control SHALL still be visible without scrolling back

### Requirement: The item's backdrop artwork is confined to the fixed region

The item's backdrop artwork SHALL extend no further down the panel than the fixed
region does, so that scrolling content never passes over or under it.

The artwork SHALL fill that region edge to edge, including the panel's top edge.
It SHALL NOT be faded, masked or inset anywhere within the region: the artwork's
strength is one number for the whole of it, so that what a reader sees at the top
of the panel is the same treatment they see at the bottom of it.

The grab handle SHALL remain distinguishable from the artwork behind it. That
outcome is unchanged; what changed is how it is reached. It was reached by
clearing the artwork away behind the handle, and it is now reached by the
handle's own colour — see `visual-design`, which states it once for every tray
rather than arranging it here for the one overlay that has a picture behind it.

#### Scenario: Artwork does not reach the scrolling content

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL end where the fixed region ends
- **AND** no scrolling content SHALL move across it

#### Scenario: The artwork is uniform across the fixed region

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL be drawn at the same strength at the panel's top
  edge as it is beside the poster
- **AND** no part of it SHALL be faded out or clipped away

#### Scenario: The grab handle stays legible

- **WHEN** the detail overlay is opened as a tray for an item with backdrop
  artwork
- **THEN** the grab handle SHALL be distinguishable from the artwork behind it

#### Scenario: No artwork is not a gap

- **WHEN** the detail overlay is opened for an item with no backdrop artwork
- **THEN** the fixed region SHALL render normally against the panel's own surface

### Requirement: Nothing is drawn between the item's title and its artwork

The detail overlay SHALL NOT draw a divider beneath the item's title.

The title sits in the fixed region, over the item's backdrop artwork. A hairline
there crosses the picture rather than separating two surfaces, and it is the
first thing the eye lands on.

The division between the fixed region and the scrolling region SHALL remain
drawn. That border is doing real work — it is where the poster and metadata stop
holding still and the summary begins to move — and it sits at the foot of the
identity block, on surface rather than on artwork.

#### Scenario: No divider under the title

- **WHEN** the detail overlay is opened
- **THEN** no divider SHALL be drawn between the title and the item's poster
  block

#### Scenario: The region division survives

- **WHEN** the detail overlay is opened
- **THEN** the boundary between the fixed region and the scrolling region SHALL
  remain visible

### Requirement: The grab handle is drawn above the item's artwork

The detail overlay's grab handle SHALL be drawn above the item's backdrop
artwork.

This is paint order and nothing else. The artwork is positioned and the handle is
not, so without it the handle is not merely dim — it is behind the picture,
whatever the artwork's opacity.

It is necessary but not sufficient on its own. The handle being *distinguishable*
once it is on top is a separate guarantee, carried by the handle's own colour and
stated in `visual-design`. The artwork SHALL NOT be cleared, faded or masked
behind the handle to achieve it.

#### Scenario: The handle is not covered by artwork

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the grab handle SHALL be drawn above that artwork

#### Scenario: The handle is legible against the brightest artwork

- **WHEN** the detail overlay is opened as a tray for an item whose backdrop
  artwork is at its brightest behind the handle
- **THEN** the handle SHALL remain distinguishable from the artwork behind it
  without any part of the artwork being cleared away

#### Scenario: The artwork still reaches the top edge

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL fill the fixed region to the panel's top edge, with
  no band of bare surface above it and no fade across it

### Requirement: The item's artwork is faint enough to read the identity block over

The item's backdrop artwork SHALL be composited over the panel's surface at a
strength low enough that every piece of text drawn over it holds a contrast ratio
of at least 4.5:1 against the artwork's worst case.

The worst case SHALL be taken as a fully white image, not as a typical one. Which
image is behind the text is chosen by the user's library, so a bar met only by
the average backdrop is a bar that fails for somebody — and it fails silently,
because the person who opened that item has no way to know the app intended
otherwise.

The bar SHALL be measured against the **dimmest** text in the fixed region, not
the title. The title is white and clears almost any backdrop; the year and the
metadata are muted grey, and they are what actually became unreadable.

Contrast is a relation between the text and what is behind it, so the artwork's
strength SHALL be chosen from that relation rather than picked for how the
picture looks on its own. The artwork is texture behind the identity block. If it
is strong enough to be read as an image, it is strong enough to compete with the
words on top of it.

#### Scenario: The muted metadata is legible over a white backdrop

- **WHEN** the detail overlay is opened for an item whose backdrop artwork is
  fully white behind the identity block
- **THEN** the year and the metadata SHALL hold at least 4.5:1 against it

#### Scenario: The artwork is still visible

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL still be distinguishable from the panel's own
  surface

### Requirement: The scrolling region is separated from the region above it

The detail overlay's scrolling region SHALL begin a visible distance below the
border that divides it from the fixed region, rather than flush against it, and
that distance SHALL be the same separation the body's sections use between
themselves.

The border marks where the item's identity stops and its description begins. A
heading set immediately beneath it reads as part of the block above rather than
as the start of a new one, and the first line of the summary is then the first
thing that looks like content.

The border is the heaviest division in the body, so it SHALL NOT be the body's
smallest gap. Reading the same separation the sections use gives the body one
rule with no exception: a heading stands one separation clear of whatever
precedes it, whether that is another section or the division.

That separation SHALL apply only to a scrolling region that has a fixed region
above it. An overlay whose body begins directly under its own title bar is
already spaced by that title bar and SHALL NOT be given the gap a second time.

#### Scenario: The Overview heading is not flush against the division

- **WHEN** the detail overlay is opened
- **THEN** the Overview heading SHALL sit a visible distance below the border
  under the poster and metadata

#### Scenario: The division is not the smallest gap in the body

- **WHEN** the detail overlay is opened
- **THEN** the distance from the division to the Overview heading SHALL equal
  the distance between two sections, and SHALL be greater than the distance from
  a heading to its own content

#### Scenario: An overlay with no fixed region is unaffected

- **WHEN** an overlay that has no pinned region above its body is opened
- **THEN** its body SHALL keep the spacing it had

### Requirement: The detail overlay's sections are separated by one distance

Every section of the detail overlay's scrolling body — Overview, Genres, Cast,
Date Added — SHALL be separated from the section before it by the same distance,
and that distance SHALL be stated once rather than restated per section.

A body whose sections sit at different distances reads as an unstructured column
with headings floating in it. The sections are the same kind of thing and
carry the same weight, so nothing about one of them may change how far it stands
from its neighbour.

That separation SHALL survive a section being added at runtime. The Date Added
section is built and appended when an item is opened, and it SHALL be spaced by
the same rule as the sections present in the markup, without carrying a marker
of its own.

#### Scenario: The gaps between sections are equal

- **WHEN** the detail overlay is opened for an item with a summary, genres and
  cast
- **THEN** the distance from the summary to the Genres heading, from the genre
  list to the Cast heading, and from the cast list to the Date Added heading
  SHALL be equal

#### Scenario: A section appended at runtime is spaced the same

- **WHEN** the Date Added section is appended to the body as the overlay opens
- **THEN** it SHALL stand the same distance from the section above it as every
  other section does, with no class or attribute added to it for that purpose

### Requirement: A heading stands nearer to what it introduces than to what precedes it

A section heading in the detail overlay's body SHALL sit closer to its own
content than to the section above it, and that closer distance SHALL be derived
from the separation between sections rather than chosen independently.

Proximity is what says a heading belongs to the block beneath it. When the two
distances are equal a heading belongs to neither; when the gap above is the
smaller one — which is the defect this replaces, at 5px above against 15px below
— every heading reads as a footer for the section above.

Deriving one distance from the other SHALL be done in the stylesheet, so that
changing the separation cannot leave a build in which a heading sits equidistant
between two sections.

#### Scenario: Every heading groups with its own content

- **WHEN** the detail overlay is opened
- **THEN** each of the Overview, Genres, Cast and Date Added headings SHALL sit
  closer to the content beneath it than to the section above it

#### Scenario: The two distances cannot drift apart

- **WHEN** the separation between sections is changed
- **THEN** the distance from a heading to its content SHALL change with it,
  because it is expressed in terms of that separation

### Requirement: A heading's leading is set by the rule that sets a heading's type

The rule that gives the detail overlay's section headings their size, weight and
colour SHALL also state their line height, so that a heading's position does not
depend on leading an ancestor set for something else.

Line height is part of the gap the eye reads: the distance runs to the glyph,
not to the top of the line box, so half the leading sits inside every gap above
and below a heading. A heading that inherits its leading therefore moves when a
container changes leading for its prose — which is how the Overview heading came
to sit lower and further from its own text than the other three, from a
`line-height` set on the summary section for the summary.

#### Scenario: All four headings share one line box

- **WHEN** the detail overlay is opened
- **THEN** the Overview, Genres, Cast and Date Added headings SHALL have the
  same line height, and the Overview heading SHALL sit at the same offset below
  its section's start as the others do

#### Scenario: Prose leading does not reach a heading

- **WHEN** a section sets a line height for its own prose
- **THEN** the heading in that section SHALL keep the line height the heading
  rule states

### Requirement: Bare prose leaves the same gap as a filled block

A section of the detail overlay's body that ends in bare text SHALL leave the
same visible gap below it as a section that ends in a filled block, and a
heading SHALL stand the same visible distance above bare text as above a filled
block.

The eye measures to the glyph for bare text and to the edge for a filled object
such as a genre pill or a cast card. A line box adds half its leading above and
below its glyphs, so identical margins produce visibly different gaps depending
on which kind of content is on each side of them — the difference is the prose's
half-leading, which at the summary's leading is about a quarter of the gap.

Prose in the body SHALL therefore withdraw its own half-leading at the edges of
its section, and the amount withdrawn SHALL be derived from that prose's own
line height so the two cannot disagree.

This SHALL apply to every bare-text block in the body, including the ones built
when an item is opened: the Date Added value, and the placeholders shown when an
item has no genres or no cast.

#### Scenario: A text-ended section and a box-ended section leave the same gap

- **WHEN** the detail overlay is opened for an item with a summary, genres and
  cast
- **THEN** the gap between the summary and the Genres heading SHALL equal the
  gap between the genre pills and the Cast heading

#### Scenario: A heading stands the same distance above text and above boxes

- **WHEN** the detail overlay is opened
- **THEN** the distance from the Overview heading to the first line of the
  summary SHALL equal the distance from the Genres heading to the genre pills

#### Scenario: A placeholder is prose too

- **WHEN** an item has no cast and the body shows a placeholder line in place of
  the cast grid
- **THEN** that line SHALL be spaced as prose, leaving the same gaps as the cast
  grid it replaced

#### Scenario: The trim follows the leading

- **WHEN** the prose line height is changed
- **THEN** the amount of half-leading withdrawn SHALL change with it, because it
  is expressed in terms of that line height

### Requirement: The foot of the body matches its sides

The space below the last section of the detail overlay's body SHALL be the
body's own padding, not that padding plus a trailing margin carried by every
section.

Spacing sections by the gap before each one rather than by a margin after each
one keeps the final distance a number that was chosen, instead of the sum of two
rules that were each written for something else.

#### Scenario: Nothing is added under the last section

- **WHEN** the detail overlay is scrolled to the end of its body
- **THEN** the space below the last line SHALL match the body's horizontal inset

