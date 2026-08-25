# visual-design Specification

## Purpose
TBD - created by archiving change convert-overlays-to-trays. Update Purpose after archive.
## Requirements
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

### Requirement: A control relocated into an overlay stays reachable at every width

Where a control is presented in the page at one viewport width and inside an
overlay at another, the width at which the page copy is withdrawn SHALL be the
width at which the overlay's trigger appears. There SHALL be no width at which
both are hidden.

A rule that hides the page copy SHALL be scoped to that copy alone. Overlay
content SHALL NOT be hidden by a rule written for the page, even where the two
share a class.

This is the failure that empties an overlay: a selector meaning "the header's
control" also matches the overlay's control, and the overlay opens with nothing
in it. Nothing errors, and the overlay's own frame renders correctly.

#### Scenario: No width hides both copies

- **WHEN** the viewport is set to any width
- **THEN** either the page's sort, genre and server controls SHALL be visible, or
  the trigger that opens the overlay carrying them SHALL be visible

#### Scenario: The Actions tray is not empty

- **WHEN** the user opens the Actions tray on a phone
- **THEN** it SHALL offer the sort, genre filter and server switch controls

#### Scenario: A page-scoped hide rule does not reach an overlay

- **WHEN** a rule hides a control that appears in the page header
- **THEN** a control of the same class inside an overlay SHALL remain visible

### Requirement: A pinned region of an overlay is part of its drag region

Where an overlay holds content fixed above its scrolling region, a downward drag
beginning on that fixed content SHALL dismiss the overlay, in the same way as a
drag beginning on the grab handle or the title bar.

The fixed region SHALL be a sibling of the scrolling region and never an ancestor
of it, so the browser does not reclaim the drag as a scroll.

A tap on a control inside the fixed region SHALL still activate that control.

#### Scenario: Dragging the pinned content dismisses

- **WHEN** the user drags downward from the fixed region of an overlay past the
  dismissal threshold
- **THEN** the overlay SHALL close

#### Scenario: A tap is not a drag

- **WHEN** the user taps a control inside an overlay's fixed region without
  moving
- **THEN** that control SHALL activate and the overlay SHALL NOT close

#### Scenario: The scrolling region still scrolls

- **WHEN** the user drags downward from the scrolling region of an overlay
- **THEN** that region SHALL scroll and the overlay SHALL NOT move

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

### Requirement: A tray offers one way to close on touch

Below the touch breakpoint, an overlay presenting as a tray SHALL offer the grab
handle as its dismissal affordance and SHALL NOT also show a close button.

Two dismissals, one of which is a small target in the corner furthest from a
thumb, is worse than one that is obvious. `.modal--tray-on-touch` already hides
its close button for this reason; a `.sheet` is a tray at that width by
definition and SHALL do the same.

Above the breakpoint, where a tray presents as a centred dialog and the handle is
hidden because there is no drag to make, the close button SHALL be shown. An
overlay SHALL never present with neither affordance.

#### Scenario: A tray shows a handle and no close button

- **WHEN** a tray is opened below the touch breakpoint
- **THEN** its grab handle SHALL be visible and its close button SHALL NOT be

#### Scenario: A dialog shows a close button and no handle

- **WHEN** the same overlay is opened above the touch breakpoint
- **THEN** its close button SHALL be visible and its grab handle SHALL NOT be

#### Scenario: Every overlay keeps an affordance at every width

- **WHEN** any overlay is opened at any width
- **THEN** at least one of its grab handle or its close button SHALL be visible

### Requirement: A head divider is not drawn across artwork

Where an overlay's head sits over the item's artwork rather than over a flat
surface, it SHALL NOT draw a divider beneath itself.

A hairline that separates two bands of surface reads as structure; the same
hairline crossing a photograph reads as a seam, and the eye finds it before it
finds the title.

Where the head sits on a flat surface the divider SHALL remain. This is a rule
about what the divider crosses, not a decision that the divider was wrong.

#### Scenario: No divider over artwork

- **WHEN** the detail overlay is opened for an item with backdrop artwork
- **THEN** no divider SHALL be drawn beneath its title

#### Scenario: The divider survives elsewhere

- **WHEN** an overlay whose head sits on a flat surface is opened
- **THEN** the divider beneath its title SHALL be drawn

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

