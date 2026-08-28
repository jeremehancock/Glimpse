## ADDED Requirements

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

## MODIFIED Requirements

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
