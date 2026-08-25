## ADDED Requirements

### Requirement: Every overlay holds its title the same distance below the grab handle

Every overlay that presents a grab handle SHALL place the first glyph of its
title the same distance below that handle, whichever shape the overlay wears.

The handle is one component. An overlay carrying it makes a promise about where
the panel begins, and the title is the first thing that promise is measured
against. Trays are opened one after another from the same screen — Actions, then
Genre, then Switch server — so a difference of two or three pixels between them
does not read as two or three pixels. It reads as the trays not sitting still.

**The distance is measured to the glyphs, not to the top of the line box.** A
line box is taller than the text inside it, and the surplus is split above and
below as half-leading. Two heads with identical padding therefore hold their
titles at different apparent heights if their titles have different
`line-height` values. Equal padding is half of this requirement, never the whole
of it.

Consequently:

- The tray head and the dialog head SHALL declare the same vertical padding.
  They MAY differ horizontally, where each matches the inset of the body beneath
  it.
- No rule SHALL set `line-height` on an overlay title. It is inherited so that
  every title's half-leading is the same number, and an override is invisible in
  every place someone would think to check.
- Where the handle is hidden because the pointer device has no drag to make, the
  head SHALL take up the spacing the handle was providing. That adjustment
  SHALL apply to exactly those heads that have a handle above them, and SHALL
  NOT reach a head that never had one.

#### Scenario: Two trays opened in turn hold their titles alike

- **WHEN** two overlays that present a grab handle are opened at the same
  viewport width
- **THEN** the distance from the bottom of the handle to the first glyph of the
  title SHALL be the same in both

#### Scenario: The two head shapes declare the same vertical padding

- **WHEN** the tray head and the dialog head rules are compared
- **THEN** their top padding SHALL be equal and their bottom padding SHALL be
  equal

#### Scenario: No overlay title overrides its line-height

- **WHEN** the stylesheets are searched for a rule that sets `line-height` on an
  element serving as an overlay's title
- **THEN** no such rule SHALL exist

#### Scenario: The handle-less head is not given the handle's spacing

- **WHEN** an overlay that never presents a grab handle is opened at a pointer
  width
- **THEN** its head SHALL NOT receive the extra top padding that stands in for a
  hidden handle

### Requirement: A rule that appears to set an element's type must set it

A style rule whose declarations are wholly outranked by another rule SHALL be
removed rather than left in place.

This is not tidiness. A rule reading `font-size`, `font-weight`, `margin` and
`line-height` on the detail overlay's title looks like the definition of that
title's type, and is where anyone goes to change it. Three of those four
declarations lose to a more specific selector and do nothing. The one that wins
is the one nobody intended, and it survived precisely because the rule around it
looked authoritative.

#### Scenario: Dead declarations are not left as documentation

- **WHEN** a declaration in a rule is outranked at every element the rule
  matches
- **THEN** the declaration SHALL be removed rather than kept alongside the live
  ones
