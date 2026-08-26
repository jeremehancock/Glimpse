## ADDED Requirements

### Requirement: A tab being dragged is lifted off the page

When a tab drag is claimed, the moving tab SHALL take on a raised presentation
for the duration of the gesture: reduced in size, given elevation and a corner
radius, with the surface behind it dimmed.

The lift arrives as the gesture is claimed rather than easing in over the drag,
so that the viewer's first frame of feedback is the confirmation that their
thumb was recognised. It is removed when the gesture resolves, by the same
routine that clears everything else the drag set.

Without it a tab sliding sideways reads as a page repainting. With it the tab
reads as a card the viewer is pushing aside — which is what the gesture is, and
what makes it feel like an application rather than a document.

The lift's scale, its elevation, its radius and the scrim SHALL be drawn from
the shared token set, not restated at the point of use.

#### Scenario: The lift appears when the gesture is claimed

- **WHEN** a horizontal tab drag is claimed
- **THEN** the moving tab SHALL be visibly raised — smaller, elevated, with
  rounded corners — and the surface behind it SHALL be dimmed

#### Scenario: The lift does not appear for a scroll or a tap

- **WHEN** a touch resolves to a vertical scroll or ends as a tap
- **THEN** no lift SHALL appear at any point

#### Scenario: The lift is removed when the gesture resolves

- **WHEN** a tab drag commits, is abandoned, or is cancelled
- **THEN** the lift, its elevation, its radius and the scrim SHALL all be
  removed

#### Scenario: The lift lands instantly under reduced motion

- **WHEN** the viewer has asked for reduced motion and a tab drag is claimed
- **THEN** the lift SHALL take effect without a visible easing

### Requirement: Direct manipulation is not reduced by a reduced-motion preference

Where the viewer is moving something with their own finger, the reduced-motion
preference SHALL govern only the motion the application plays on its own — the
settle after release — and SHALL NOT suppress the element's correspondence to
the touch.

Reduced motion exists to remove motion the viewer did not ask for. A drag is
motion the viewer is producing: suppressing it would not calm the interface, it
would make the gesture unusable, leaving the viewer with a page that refuses to
acknowledge their thumb until they lift it.

This is stated so the app-wide rule is not later extended over the follow on
the reasonable-looking grounds that it is an animation.

#### Scenario: A dragged element still follows the finger

- **WHEN** the viewer has requested reduced motion and drags a tab or an
  overlay
- **THEN** the dragged element SHALL follow the touch exactly as it does
  otherwise

#### Scenario: The released settle is instant

- **WHEN** the viewer has requested reduced motion and releases a drag
- **THEN** the element SHALL reach its resting position without a sustained
  animation, and any state that depends on that movement completing SHALL
  still resolve
