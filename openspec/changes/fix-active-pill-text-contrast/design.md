## Context

Three pill controls in the header switch between a neutral fill and the accent
fill by toggling an `.active` class:

| Control | Base rule | Selected rule |
| --- | --- | --- |
| `.tab` | `web/index.html:295` | `web/index.html:307` |
| `.sort-button` | `web/index.html:406` | `web/index.html:423` |
| `.genre-button` | `web/index.html:406` | `web/index.html:423` |

Each base rule carries `transition: all var(--transition-speed)` — 0.3s — and
each selected rule sets both `background-color: var(--primary-color)` and
`color: #000`. `all` therefore transitions the label colour alongside the fill.

That is the defect. Selecting a tab drives its label from white to black over
the same 300ms that drives its pill from `#333` to `#e5a00d`; deselecting drives
it back. Halfway through either direction the label is mid-grey and the pill is
still substantially accent-coloured, and mid-grey on Plex yellow has almost no
contrast. It reads exactly as reported: white text on the yellow button.

Two smaller things about the same rules are worth fixing in the same pass, and
only in the same pass:

- `.tab` declares no `color` at all. It is a `<div>`, so it inherits white and
  renders correctly — but the rule that decides the resting label colour is not
  the rule anyone would open to change it. `.sort-button` already declares
  `color: var(--light-text)`, so the two halves of one pattern disagree.
- `all` is what pulled `color` in without anyone writing it down, and it will do
  the same to the next property added to these rules.

Constraints: `web/` is served as authored — no build step, no bundler, no
preprocessing. CI has no browser, so nothing here can be verified by CI in the
way a human verifies it.

## Goals / Non-Goals

**Goals:**

- The label is legible on every frame of a selection change, in all three
  server palettes.
- The fill keeps easing. This is a contrast fix, not a de-animation.
- The three controls stay one pattern rather than three near-copies.
- The decision is pinned in a test, since a browser cannot pin it here.

**Non-Goals:**

- Changing either fill colour, the accent tokens, or the black-on-accent
  contrast choice itself. Black on `#e5a00d` and on `#52c41a` is the right
  call; the resting states were never the problem.
- Controls that are accent-filled at rest and never cross: `.genre-badge`
  (`:1668`), `.scroll-to-top` (`:945`), `.roulette-close-btn` (`:5240`).
- `.genre-item.active` (`web/index.html:506`), which moves from a light
  inherited colour to `var(--primary-color)` over a dark tinted fill. Both ends
  and every midpoint are light-on-dark. It already names its transitioned
  properties explicitly, `color` among them, and that is correct there.
- The other `transition: all` declarations — `.tabs` (`:292`), `.search-input`
  (`:344`), `.server-toggle-button` (`:1676`). None of them cross fills. Folding
  them in would turn a contrast fix into a stylesheet refactor and make the
  diff impossible to review as either.

## Decisions

### Switch the label colour rather than shortening its transition

The label's job is to be readable. A colour that is readable at both ends and
unreadable in between is not a fade between two states — it is a third state
nobody designed. Shortening `color`'s duration to something imperceptible
(80ms, say) would hide the symptom while leaving a number that has to be right,
and the value that is actually correct for that number is zero.

Alternatives considered:

- **Ease `color` faster than `background-color`.** Still an interpolation,
  still passes through mid-grey, and now the ratio between two durations is
  load-bearing and undocumented.
- **Make the accent-fill label white instead of black.** Removes the crossing by
  removing one end of it, at the cost of the resting contrast: white on
  `#e5a00d` is roughly 2:1 and worse than what is being fixed. Black on the
  accent is not in question.
- **Give the pill a solid label colour and animate opacity.** More machinery
  than the problem needs, and it would fade the label out mid-change — visually
  the same complaint.

### Name the transitioned properties

`transition: background-color var(--transition-speed), box-shadow
var(--transition-speed)` on each base rule. `box-shadow` is named because
`.tab.active` adds `var(--shadow-sm)` and that easing is wanted.

The list is what makes the omission of `color` legible: a reader sees which
properties animate and that the label is not among them. With `all` plus an
override, the fact would live in two places and have to be assembled.

Alternative considered: keep `all` and add `transition-property` exclusions —
CSS has no such thing. `all` plus `transition: color 0s` would work and states
the same fact in a way that reads as an accident.

### Declare the resting label colour on `.tab`

`color: var(--light-text)` in the base rule. It changes no rendered pixel today
— the inherited value is `--light-text` — so the risk is nil and the payoff is
that the pair of rules deciding this label's colour are both visible.

This is the existing spec rule about rules that appear to set an element's type,
approached from the other side: there, a rule looked authoritative and was dead;
here, the authoritative rule is missing and inheritance is doing the work
silently.

### Pin it as a source shape, not a rendered result

`tests/test_pill_contrast.py`, following `tests/test_cache_policy.py` — assert
the shape of the source, because the thing that would catch it in a browser does
not exist in CI.

The assertion: for each of the three base rules, the declared `transition` names
its properties, does not use `all`, and does not include `color`; and each base
rule declares a `color`. Parsed from the rule bodies by name, so a rule that is
renamed or split fails loudly rather than silently passing on a regex that no
longer matches anything — the "live code that cannot succeed" failure this repo
has shipped before.

Alternative considered: a broader assertion over every rule in the stylesheet
that sets `background-color: var(--primary-color)`. Rejected — it would sweep in
the always-accent controls, which have no crossing and no reason to be
constrained, and the test would then be enforcing something the spec does not
say.

### Verification is by eye, and the eye needs slow motion

A 300ms wash is exactly the duration that is obvious when you know to look and
deniable when you do not. Verify with DevTools animation playback slowed to
10–25%, or by temporarily raising `--transition-speed`, and check the crossing
in **both** directions on at least the Plex palette — deselection is the
direction where the label goes light while the pill is still yellow, which is
the reported symptom. `transition: all` being gone is not proof that the label
stopped moving; sample the computed `color` across the change.

## Risks / Trade-offs

- **The instant colour switch looks abrupt next to the easing fill.** →
  Unlikely to read as abrupt at all: the eye tracks the pill's fill, and text
  that is simply correct throughout is not something a viewer notices. If it
  does read badly, the answer is to shorten the *fill*, not to re-animate the
  label.
- **Naming properties means a future declaration gets no transition and nobody
  notices.** → That is the trade being made, and it is the right way round: a
  missing transition is visible, an unwanted one on a layout property is not.
  The spec states it so the next person does not "fix" it back to `all`.
- **The test pins rule names, so renaming a control breaks it.** → Intended. A
  rename is exactly when someone should be re-reading this decision, and a test
  that quietly matches nothing is worse than one that fails.
- **`make test` cannot tell you the change worked**, only that the source still
  says what it decided. → Same limitation as the grid-windowing and
  tab-transition tests, and handled the same way: the test pins the decision,
  a human confirms the picture on the `:dev` image before archiving.
