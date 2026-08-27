## ADDED Requirements

### Requirement: A label crossing between fills is switched, never interpolated

A control that changes between the neutral fill and the accent fill SHALL change
its label colour instantly at the moment the state changes. The fill MAY ease;
the label colour SHALL NOT be transitioned, and SHALL NOT be swept into a
transition by `all`.

Legibility is a correctness property of a label, not a look. The two fills sit
at opposite ends of the app's brightness range, so their labels do too — white
on the neutral fill, black on the accent. Easing both together does not fade one
legible state into another: it drives the text through mid-grey at the same rate
it drives the pill through mid-accent, and the midpoint of that pair has almost
no contrast at all. On the Plex yellow the label all but disappears.

The duration does not rescue it. The wash lands on the click, is the same length
as the app's standard transition, and sits on the control the viewer is looking
at because they are operating it.

A control that is accent-filled at rest, or that moves between two colours on
the same side of the range, is not crossing and is not covered here.

#### Scenario: A tab is selected

- **WHEN** the viewer selects the Movies or TV Shows tab
- **THEN** that tab's label SHALL take its accent-fill colour immediately, and
  SHALL be fully legible on every frame of the fill's change

#### Scenario: A tab is deselected

- **WHEN** a tab loses selection because the other was chosen
- **THEN** its label SHALL take its neutral-fill colour immediately, and SHALL
  NOT pass through a low-contrast value while the accent fill drains away

#### Scenario: The sort and genre pills change state

- **WHEN** a sort or genre pill gains or loses its selected state
- **THEN** its label SHALL change colour instantly, on the same terms as a tab

#### Scenario: The rule holds for every server palette

- **WHEN** the app is themed for Plex, Jellyfin or Emby
- **THEN** the label SHALL be switched rather than interpolated in each, because
  the defect is the crossing and not the particular accent

### Requirement: A control states its own resting label colour

A control whose selected state sets a label colour SHALL also state that
label's resting colour on the control itself, rather than leaving it to
inheritance.

Inheritance makes the resting colour invisible at the place it is decided. The
tab's selected rule names a colour and its base rule names none, so the base
rule reads as though the label has no colour of its own — the pair only makes
sense to someone who already knows the answer. It is the same failure as a rule
whose declarations are outranked: the code that looks authoritative is not the
code that decides.

#### Scenario: The resting colour is declared

- **WHEN** a rule sets a label colour for a control's selected state
- **THEN** the control's base rule SHALL declare the resting label colour
  explicitly

### Requirement: A control transitions the properties it animates, not `all`

A control described by this capability SHALL name the properties it transitions.
`transition: all` SHALL NOT be used where the control also changes a property
that must not be animated.

`all` is how the label colour joined the fade: nobody chose to animate it, and
nothing in the rule says it is animated. It also enrols every property added
afterwards, so the next declaration added to the rule acquires a transition
silently — including a layout property, which is the expensive kind.

#### Scenario: A transition names its properties

- **WHEN** a control changes fill and label colour together
- **THEN** its transition SHALL name the fill and any other property it means to
  animate, and the label colour SHALL be absent from that list

#### Scenario: The prohibition is checkable without a browser

- **WHEN** the test suite runs
- **THEN** it SHALL fail if a rule that toggles the accent fill also transitions
  `color`, whether named directly or by `all`
