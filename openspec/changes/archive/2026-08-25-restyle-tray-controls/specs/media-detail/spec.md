## ADDED Requirements

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
