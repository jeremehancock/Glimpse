## ADDED Requirements

### Requirement: A fill and its label change on the same frame

A control that changes between the neutral fill and the accent fill SHALL change
its fill and its label colour on the same frame. Neither SHALL be transitioned,
and neither SHALL be swept into a transition by `all`.

Legibility is a correctness property of a label, not a look. The two fills sit
at opposite ends of the app's brightness range, so their labels do too — white
on the neutral fill, black on the accent. A label is therefore only legible
against its own fill, which makes the fill and the label one pair: whenever one
arrives without the other, the control wears the wrong label for the whole
duration.

**Every ordering was tried, and all three fail.** This is stated at length
because two of them look like fixes for the third:

- **Both eased.** The text crosses mid-grey at the same rate the pill crosses
  mid-accent. The midpoint of that pair has almost no contrast; on the Plex
  yellow the label all but disappears.
- **The fill eased, the label switched.** Deselecting puts a fully white label
  on a fully yellow pill on the first frame, and holds it while the yellow
  drains. This is *worse* than easing both, where the label is at least still
  dark when the pill is at its brightest — and it is the version that reached a
  user. Selecting has the mirror flaw, black on the dark neutral fill, which
  reads as dim rather than wrong and so goes unreported.
- **The label eased, the fill switched.** The same defect reflected.

There is no ordering that escapes it, so neither half moves. **A selected state
is a state, not an animation.** Where a control's selection coincides with
motion the app already plays — a tab click also slides the page — that motion
carries the change, and a 300ms pill fade adds nothing a viewer can attribute.

The duration is not a defence. The wash lands on the click, lasts as long as the
app's standard transition, and sits on the control the viewer is looking at
because they are operating it.

A control that is accent-filled at rest, or that moves between two colours on
the same side of the brightness range, is not crossing and is not covered here.
A transition over a property that does not bear on the label's contrast — a
shadow, a transform — remains permitted.

#### Scenario: A tab is selected

- **WHEN** the viewer selects the Movies or TV Shows tab
- **THEN** that tab SHALL take the accent fill and its accent-fill label colour
  on the same frame, and SHALL be fully legible on every frame of the change

#### Scenario: A tab is deselected

- **WHEN** a tab loses selection because the other was chosen
- **THEN** it SHALL take the neutral fill and its neutral-fill label colour on
  the same frame, and SHALL NOT show a light label over a draining accent fill
  on any frame

#### Scenario: The sort and genre pills change state

- **WHEN** a sort or genre pill gains or loses its selected state
- **THEN** its fill and label SHALL change together, on the same terms as a tab

#### Scenario: The rule holds for every server palette

- **WHEN** the app is themed for Plex, Jellyfin or Emby
- **THEN** the pair SHALL change together in each, because the defect is the
  crossing and not the particular accent

#### Scenario: A property unrelated to contrast may still ease

- **WHEN** a crossing control transitions a property that does not change the
  contrast between its label and its fill
- **THEN** that transition SHALL be permitted

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

A control that has nothing left to animate SHALL declare no transition at all,
rather than a transition naming properties it does not change. A declaration
that cannot fire is the shape this project has shipped before: it reads as a
working feature to everyone who opens the file.

#### Scenario: A transition names its properties

- **WHEN** a crossing control transitions anything
- **THEN** its transition SHALL name each property, and both the fill and the
  label colour SHALL be absent from that list

#### Scenario: A control with nothing to animate declares nothing

- **WHEN** every property a control would transition is one it must not
- **THEN** the rule SHALL carry no `transition` declaration

#### Scenario: The prohibition is checkable without a browser

- **WHEN** the test suite runs
- **THEN** it SHALL fail if a rule that toggles the accent fill transitions
  either `color` or its fill, whether named directly or by `all`
