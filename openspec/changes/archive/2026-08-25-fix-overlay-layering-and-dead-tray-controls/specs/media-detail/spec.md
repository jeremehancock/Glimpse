## ADDED Requirements

### Requirement: The grab handle stays legible over any item's artwork

The detail overlay's grab handle SHALL be drawn above the item's backdrop
artwork, and the artwork SHALL be fully transparent across the whole area the
handle occupies.

Both halves are required. The artwork is positioned and the handle is not, so
paint order alone puts the artwork on top whatever its opacity; and lifting the
handle without clearing the artwork behind it leaves a grey bar over an arbitrary
photograph, whose legibility then depends on which item was opened.

The distance over which the artwork clears SHALL be derived from the handle's
own metrics rather than restated, and SHALL extend past the handle's lower edge
rather than ending at it.

The artwork SHALL still reach the panel's top edge — the full-bleed appearance is
deliberate, and moving the artwork down instead would leave a band of bare
surface reading as a gap.

#### Scenario: The handle is not covered by artwork

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the grab handle SHALL be drawn above that artwork

#### Scenario: The artwork is clear behind the handle

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL be fully transparent over the handle and for a
  margin below its lower edge

#### Scenario: The artwork still reaches the top edge

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL fill the fixed region to the panel's top edge, with
  no band of bare surface above it
