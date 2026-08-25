## ADDED Requirements

### Requirement: The roulette is a tray on touch and a dialog on a pointer device

The roulette overlay SHALL present as a bottom tray below the touch breakpoint
and as a centred dialog above it, like the detail overlay.

It is the last overlay still centred at every width. On a phone that leaves one
overlay arriving from the middle of the screen while every other one rises from
the bottom edge, which reads as an oversight rather than as a distinction.

To present as a tray it SHALL carry the three regions the overlay system
requires: a grab handle, a head, and a body. It has none of them today — it is a
panel wrapping a spinner — so this is structural rather than a modifier class.
Adding the modifier alone would produce a tray with nothing to drag and, because
the modifier hides the close button on touch, no way to dismiss it.

The drag region and the scrolling region SHALL remain separate elements, as for
every other overlay.

#### Scenario: A tray on a phone

- **WHEN** the roulette is opened below the touch breakpoint
- **THEN** it SHALL be docked to the bottom edge, span the full width, and show
  its grab handle

#### Scenario: A dialog on a desktop

- **WHEN** the roulette is opened above the touch breakpoint
- **THEN** it SHALL be centred and SHALL show its close button

#### Scenario: It can be dismissed on touch

- **WHEN** the roulette is open on a phone and the user drags its handle
  downward past the dismissal threshold
- **THEN** the overlay SHALL close

### Requirement: The roulette names itself and can be closed

The roulette overlay SHALL carry a visible title, and SHALL offer a close control
at every width — the close button on a pointer device, the grab handle on touch.

Today it offers neither outside its error state: while it is choosing there is no
close control at all, and dismissing by backdrop is deliberately suppressed. An
overlay that cannot be dismissed while it works is tolerable only while the work
is brief, and it stops being tolerable the moment anything hangs.

Suppressing backdrop dismissal while it is choosing SHALL remain. A stray tap
cancelling a pick the user just asked for reads as the control not working; that
reasoning is unchanged and is why the affordances above are explicit ones.

#### Scenario: The overlay is named

- **WHEN** the roulette is opened
- **THEN** a visible title SHALL identify it, and the overlay SHALL expose that
  name to assistive technology

#### Scenario: It can be closed while choosing

- **WHEN** the roulette is choosing and the user activates its close affordance
- **THEN** the overlay SHALL close

#### Scenario: The backdrop still does not dismiss it

- **WHEN** the roulette is choosing and the user taps the backdrop
- **THEN** the overlay SHALL remain open
