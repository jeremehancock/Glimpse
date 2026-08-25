## ADDED Requirements

### Requirement: Page chrome ranks below every overlay

Every element of the page's own chrome — the header, the scroll-to-top control,
the swipe indicator, and anything else fixed to the viewport that is not an
overlay — SHALL carry a stacking order below the lowest overlay tier.

The layering scale SHALL be declared once as design tokens and read from there.
A chrome element SHALL NOT state a stacking order as a literal of its own.

This is not a cosmetic ordering. An overlay's backdrop exists to withdraw the
page behind it; chrome that outranks the backdrop is neither dimmed nor blurred,
so the overlay reads as sliding in *behind* the page rather than over it. Where
the overlay is tall enough to reach under the header, the header covers its
title bar and its grab handle outright.

#### Scenario: A dialog covers the header

- **WHEN** the media detail overlay is open at a pointer-device width
- **THEN** its panel and its backdrop SHALL be painted above the page header

#### Scenario: A tray covers the header

- **WHEN** any tray is open at a touch width
- **THEN** the header SHALL be dimmed and blurred by that tray's backdrop like
  the rest of the page

#### Scenario: Chrome does not outrank the overlay scale

- **WHEN** the stylesheet is inspected
- **THEN** no element of the page's chrome SHALL declare a stacking order
  greater than or equal to the lowest overlay tier

### Requirement: A control inside a teleported overlay is operable

Where an overlay is moved elsewhere in the document when the page initialises,
every control inside it SHALL carry its behavior by the time the overlay can be
opened.

A control SHALL NOT be left bound only to the code that dismisses the overlay
containing it. A tap that closes an overlay and does nothing else is
indistinguishable from a tap that worked, so this failure reports as the feature
being missing rather than as an error.

Page wiring that finds its subjects by searching the document SHALL run after
the document holds the overlay's final markup, or SHALL be re-run against it.

#### Scenario: Every control in the Actions tray carries a handler

- **WHEN** the Actions tray is opened on a phone
- **THEN** each of its controls SHALL have behavior bound beyond dismissing the
  tray

#### Scenario: A relocated control behaves as its page counterpart does

- **WHEN** a control appears both in the page and inside a teleported overlay
- **THEN** activating either copy SHALL produce the same result
