## MODIFIED Requirements

### Requirement: The item's backdrop artwork is confined to the fixed region

The item's backdrop artwork SHALL extend no further down the panel than the fixed
region does, so that scrolling content never passes over or under it.

The artwork SHALL fill that region edge to edge, including the panel's top edge.
It SHALL NOT be faded, masked or inset anywhere within the region: the artwork's
strength is one number for the whole of it, so that what a reader sees at the top
of the panel is the same treatment they see at the bottom of it.

#### Scenario: Artwork does not reach the scrolling content

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL end where the fixed region ends
- **AND** no scrolling content SHALL move across it

#### Scenario: The artwork is uniform across the fixed region

- **WHEN** the detail overlay is opened for an item that has backdrop artwork
- **THEN** the artwork SHALL be drawn at the same strength at the panel's top
  edge as it is beside the poster
- **AND** no part of it SHALL be faded out or clipped away

#### Scenario: No artwork is not a gap

- **WHEN** the detail overlay is opened for an item with no backdrop artwork
- **THEN** the fixed region SHALL render normally against the panel's own surface

### Requirement: The grab handle stays legible over any item's artwork

The detail overlay's grab handle SHALL be drawn above the item's backdrop
artwork.

This is paint order, and it is necessary but no longer sufficient on its own. The
artwork is positioned and the handle is not, so without the lift the artwork
covers the handle whatever its opacity. The other half — the handle being
distinguishable from what is behind it once it is on top — is now carried by the
handle's own colour, stated once in `visual-design` for every tray rather than
arranged here by clearing the artwork away behind this one.

The artwork SHALL NOT be cleared, faded or masked behind the handle. That
arrangement was replaced, not relaxed: it made the handle's legibility a property
of the detail overlay's artwork rather than of the handle, so every other tray's
handle was left unverified — and it was, in fact, failing the same bar against
plain surface the whole time.

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

## ADDED Requirements

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
border that divides it from the fixed region, rather than flush against it.

The border marks where the item's identity stops and its description begins. A
heading set immediately beneath it reads as part of the block above rather than
as the start of a new one, and the first line of the summary is then the first
thing that looks like content.

That separation SHALL apply only to a scrolling region that has a fixed region
above it. An overlay whose body begins directly under its own title bar is
already spaced by that title bar and SHALL NOT be given the gap a second time.

#### Scenario: The Overview heading is not flush against the division

- **WHEN** the detail overlay is opened
- **THEN** the Overview heading SHALL sit a visible distance below the border
  under the poster and metadata

#### Scenario: An overlay with no fixed region is unaffected

- **WHEN** an overlay that has no pinned region above its body is opened
- **THEN** its body SHALL keep the spacing it had
