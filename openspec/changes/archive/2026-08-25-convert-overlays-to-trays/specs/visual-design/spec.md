## ADDED Requirements

### Requirement: One overlay presentation serves every overlay

The application SHALL present every overlay through one shared system with two
shapes: a **tray** docked to the bottom edge, and a **dialog** centred in the
viewport. Both SHALL provide a backdrop, a grab handle, a head carrying a title,
and a body that scrolls independently of the head.

An overlay MUST NOT implement its own show, hide, backdrop, or dismissal
behavior.

#### Scenario: Every overlay uses the shared presentation

- **WHEN** any of the menu, server switcher, genre filter, media detail, trailer
  or roulette overlays is opened
- **THEN** it SHALL render a backdrop, a grab handle, a titled head, and a
  scrollable body from the shared overlay markup

#### Scenario: The panel clips and the body scrolls

- **WHEN** an overlay's content is taller than the space available
- **THEN** the body SHALL scroll and the head and grab handle SHALL remain
  visible

#### Scenario: Scrolling does not chain to the page

- **WHEN** the user scrolls an overlay's body to its end and continues
- **THEN** the page behind the overlay SHALL NOT scroll

### Requirement: A tray on touch, a dialog on a pointer device

The media detail overlay, the menu, the server switcher and the genre filter
SHALL be presented as a tray on narrow, touch-first viewports and as a centred
dialog on wide viewports. The trailer and roulette overlays SHALL be presented as
dialogs at every width, being sized to their content rather than to the screen.

#### Scenario: Detail view on a phone

- **WHEN** the media detail overlay is opened on a narrow viewport
- **THEN** it SHALL be docked to the bottom edge and SHALL slide up from it

#### Scenario: Detail view on a desktop

- **WHEN** the media detail overlay is opened on a wide viewport
- **THEN** it SHALL be centred in the viewport

#### Scenario: The trailer is a dialog at every width

- **WHEN** the trailer overlay is opened on a narrow viewport
- **THEN** it SHALL be centred rather than docked to the bottom edge

#### Scenario: The grab handle is a touch affordance only

- **WHEN** an overlay is presented as a centred dialog on a pointer device
- **THEN** the grab handle SHALL NOT be shown, and the overlay SHALL offer a
  close control instead

### Requirement: An overlay can be dismissed by dragging it down

A downward drag beginning on an overlay's grab handle or head SHALL dismiss it.
A drag beginning in the scrolling body SHALL NOT.

The gesture SHALL be implemented once, at the document level, and SHALL dismiss
by invoking the overlay's own backdrop close rather than by knowing which overlay
it is acting on — so that an overlay added later inherits it.

The drag region and the scrolling region MUST remain separate elements: the drag
region suppresses the browser's own touch handling, which the browser honours
only when that region is not itself the scroller.

#### Scenario: Dragging the handle down dismisses

- **WHEN** the user drags an overlay's grab handle downward past the dismissal
  threshold and releases
- **THEN** the overlay SHALL close

#### Scenario: A short drag settles back

- **WHEN** the user drags an overlay's grab handle downward less than the
  dismissal threshold and releases
- **THEN** the overlay SHALL return to its open position and remain open

#### Scenario: Dragging the body scrolls rather than dismisses

- **WHEN** the user drags downward starting inside an overlay's scrolling body
- **THEN** the body SHALL scroll and the overlay SHALL remain open

#### Scenario: A released drag does not freeze the panel

- **WHEN** a partly-dragged overlay is released and then dismissed
- **THEN** the panel SHALL animate out with its backdrop rather than remaining
  where the drag left it

### Requirement: The page does not scroll behind an open overlay

While any overlay is open the page behind it SHALL NOT scroll, and the scroll
position SHALL be restored when the last overlay closes.

An overlay that is animating closed SHALL NOT count as open. Waiting for it holds
the page locked for the length of every dismissal, so the first gesture after
closing an overlay is swallowed.

#### Scenario: The page is locked while an overlay is open

- **WHEN** an overlay is open and the user drags on its backdrop
- **THEN** the page behind SHALL NOT scroll

#### Scenario: Scroll position survives an overlay

- **WHEN** the user scrolls the library, opens an overlay, and closes it
- **THEN** the library SHALL be at the same scroll position as before

#### Scenario: Scrolling resumes immediately after dismissal

- **WHEN** the user dismisses an overlay and immediately scrolls
- **THEN** the page SHALL scroll

#### Scenario: The layout does not shift when an overlay opens

- **WHEN** an overlay opens on a viewport with a visible scrollbar
- **THEN** the content behind SHALL NOT shift horizontally

### Requirement: An overlay is focus-managed because it declares itself a dialog

An overlay's panel SHALL declare `role="dialog"`, `aria-modal="true"` and
`tabindex="-1"`. Focus SHALL move into the panel when it opens and SHALL return
to its origin when it closes.

The focus manager SHALL find its subjects by that attribute rather than by a
registry, so that an overlay is managed by being marked up correctly rather than
by being registered — including one created at runtime.

The origin SHALL be remembered as a chain of ancestors rather than a single
element, because the element that opened an overlay is often gone by the time
focus is returned. The chain SHALL stop short of the document body: an origin of
the body is what a touch interaction leaves behind, and restoring focus there is
the failure this requirement exists to prevent, so an empty chain SHALL restore
nothing.

#### Scenario: Focus enters an opened overlay

- **WHEN** a keyboard user activates a control that opens an overlay
- **THEN** focus SHALL move to the overlay's panel

#### Scenario: Focus returns on close

- **WHEN** a keyboard user dismisses an overlay
- **THEN** focus SHALL return to the control that opened it

#### Scenario: Focus returns near a removed origin

- **WHEN** an overlay is dismissed and the control that opened it no longer
  exists
- **THEN** focus SHALL move to the nearest ancestor still in the document

#### Scenario: A touch-originated overlay does not steal focus back

- **WHEN** an overlay opened by a touch interaction is dismissed
- **THEN** focus SHALL NOT be moved to the document body

#### Scenario: A closing overlay does not hold focus

- **WHEN** an overlay is animating closed
- **THEN** it SHALL NOT be treated as an open dialog by the focus manager

### Requirement: A control that closes one overlay to open another moves focus first

A control that dismisses its own overlay and opens a different one SHALL move
focus to an element still on screen before its overlay hides.

Hiding a focused element hands its focus to the document body, which the focus
manager reads a frame later to decide where to return focus to — and an origin
rooted at the body is the one case it declines to restore. The second overlay
opens correctly and focus lands in it correctly; the failure appears only on
dismissing it, when the keyboard user is left at the top of the page. Nothing
errors, and the pointer path is unaffected.

#### Scenario: Chained overlays restore focus correctly

- **WHEN** a keyboard user opens an overlay from a control inside another
  overlay, and then dismisses the second one
- **THEN** focus SHALL return to a control in the first overlay rather than to
  the top of the page

### Requirement: Escape closes the topmost overlay

Pressing Escape SHALL close the overlay currently on top, leaving any overlay
beneath it open.

#### Scenario: Escape closes an overlay

- **WHEN** an overlay is open and the user presses Escape
- **THEN** that overlay SHALL close

#### Scenario: Escape closes only the topmost

- **WHEN** an overlay opened from within another overlay is on top and the user
  presses Escape
- **THEN** the topmost SHALL close and the one beneath SHALL remain open

### Requirement: Overlays are drawn from a shared token set

Surface colours, borders, radii, elevation, transition durations and easings used
by overlays SHALL be declared once as custom properties and referenced by every
overlay. An overlay MUST NOT restate these values.

Overlay layering SHALL be a single ordered scale, so that a dialog raised from
inside a tray renders above it — a confirmation drawn behind the tray that asked
the question cannot be answered.

#### Scenario: One declaration of the overlay surface

- **WHEN** the overlay surface colour is changed in the token set
- **THEN** every overlay SHALL reflect the change without further edits

#### Scenario: A dialog raised from a tray sits above it

- **WHEN** a dialog is opened from a control inside a tray
- **THEN** the dialog SHALL render above the tray

### Requirement: Overlay motion honours a reduced-motion preference

When the user has asked for reduced motion, overlay transitions SHALL be
effectively instant. The preference SHALL be honoured by a single app-wide rule
rather than per overlay.

An overlay moves the largest area of the screen of anything in the application,
so it is the most consequential place for this to be missed.

#### Scenario: No animation under reduced motion

- **WHEN** the user has requested reduced motion and opens an overlay
- **THEN** the overlay SHALL appear without a slide or scale animation

#### Scenario: Overlays still open and close under reduced motion

- **WHEN** the user has requested reduced motion
- **THEN** every overlay SHALL still open, close, and restore focus normally

### Requirement: A dismissed overlay stops accepting input immediately

An overlay that is animating closed SHALL NOT receive pointer input.

The element remains displayed for the length of its leave animation, so without
this a dismissed overlay goes on swallowing clicks while it fades: the user
dismisses it, reaches for what is behind it, and the interaction lands on a
backdrop that is visually almost gone.

#### Scenario: Clicks pass through a closing overlay

- **WHEN** the user dismisses an overlay and immediately activates a control
  behind it
- **THEN** that control SHALL receive the interaction
