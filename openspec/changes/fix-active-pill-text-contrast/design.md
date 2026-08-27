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

### CORRECTION: the fill and the label are one pair, so neither eases

**This decision was originally written as "switch the label, let the fill ease",
and that was wrong.** It shipped, and a user reported the result: deselecting a
tab put a fully white label on a fully yellow pill and held it for the 300ms the
fill took to drain. That is worse than the defect it replaced, where both eased
and the label was at least still dark while the pill was at its brightest.

The error was in the model, not the code. "Which property is causing the bad
frames?" has no answer, because contrast is a relation between two properties
and not a fact about either. Once one is instant and the other is not, there is
a window where they disagree — and moving the instant one to the other side just
reflects the window:

| Fill | Label | Result |
| --- | --- | --- |
| eased | eased | text crosses mid-grey while the pill crosses mid-accent |
| eased | switched | **white label on a full-yellow pill** on deselection |
| switched | eased | the same, reflected |
| switched | switched | correct on every frame |

Only the last row has no bad frame, so that is the rule: they change together,
which in CSS means neither is transitioned.

The mirror flaw is worth naming because it went unreported. With the fill eased
and the label switched, *selecting* a tab puts a black label on the dark neutral
fill for the same 300ms. It is just as illegible; it reads as dim rather than
lurid, and the page slide pulls the eye away. **A defect that only presents in
one direction is still present in both** — the reported symptom was the loud
half of a symmetric bug, and fixing only what was reported is what produced the
second version.

Alternatives considered:

- **Ease the fill in, switch it out** — put the transition on `.tab.active`, so
  the after-change style supplies it. Correct on deselection, still black-on-
  dark on selection, and CSS cannot distinguish "just lost `.active`" from
  "hovering while inactive": both are `.tab:not(.active)`.
- **Shorten `color`'s duration to something imperceptible** (80ms, say). Hides
  the symptom while leaving a number that has to be right, and the value that is
  actually correct for that number is zero.
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

### Remove the transition rather than narrow it

With both halves of the pair barred and `box-shadow` the only thing left, the
honest rule declares no transition at all. Keeping `transition: box-shadow` to
ease `--shadow-sm` alone would leave a shadow drifting in after the fill it
belongs to had already snapped.

Alternatives considered: keep `all` and add `transition-property` exclusions —
CSS has no such thing. `all` plus `transition: color 0s, background-color 0s`
states the same fact in a way that reads as an accident.

### Accept that the hover tint snaps too

Hover and selection both change `background-color`, and CSS cannot tell "just
lost `.active`" from "hovering while inactive" — both are `.tab:not(.active)`,
so any transition serving the hover ease also serves the deselection wash. The
hover tint therefore becomes instant.

It could have been kept: painting the accent fill with `background-image:
linear-gradient(accent, accent)` puts it outside the `background-color`
transition, so hover eases and the selected state snaps. Rejected — a solid
gradient used to dodge a transition reads as a mistake to the next person, and
it buys the ease on a `rgba(255, 255, 255, 0.1)` tint nobody has asked for. An
instant hover response is not a worse one.

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

The assertion: for each base rule, neither `color` nor `background-color` is
transitioned — directly or by `all` — and each base rule declares a `color`. A
transition over anything else stays permitted, so the test constrains the pair
rather than banning motion. Parsed from the rule bodies by name, so a rule that
is renamed or split fails loudly rather than silently passing on a regex that no
longer matches anything — the "live code that cannot succeed" failure this repo
has shipped before.

**The first version of this test named only `color`, and it passed the build
that reached the user.** That is the lesson worth keeping: the test encoded the
requirement faithfully, and the requirement was wrong. A test derived from a
spec inherits the spec's blind spot, so it can confirm an intention and never
challenge it. Nothing here was going to catch this except a person looking at
the screen — which is why group 3 of `tasks.md` is not optional, and why the
mutation pass now drives each of the three failing orderings through the
assertions rather than only the one that was reported.

Alternative considered: a broader assertion over every rule in the stylesheet
that sets `background-color: var(--primary-color)`. Rejected — it would sweep in
the always-accent controls, which have no crossing and no reason to be
constrained, and the test would then be enforcing something the spec does not
say.

### Verification is by eye, and it needs both directions

A 300ms wash is exactly the duration that is obvious when you know to look and
deniable when you do not. Verify with DevTools animation playback slowed to
10–25%, and check **both** directions on at least the Plex palette.

Both, specifically, because checking one is how the second version shipped:
selection was verified, looked better, and the mirror flaw sat in the direction
nobody watched. Deselection is the loud one — a light label over a draining
yellow. Selection is the quiet one — a black label on the dark neutral fill,
which is equally illegible and reads as nothing being wrong.

`transition: all` being gone is not proof that anything stopped moving. Sample
the computed `color` and `background-color` together across the frames of the
change; what must be true is that they step on the same frame.

## Risks / Trade-offs

- **The pill's state change is now instant and may read as abrupt.** → It should
  not: on a tab click the page slide supplies the motion, and the pill snapping
  under it is not something a viewer can separate out. If it does read badly,
  the answer is a transition on something that does not bear on contrast — a
  shadow, a transform — never on the fill or the label.
- **The hover tint no longer eases.** → Accepted, and stated in the decision
  above. An instant hover response is not a worse one, and the alternative that
  preserves it costs more legibility in the source than it buys on screen.
- **A future declaration on these rules gets no transition and nobody notices.**
  → That is the trade, and it is the right way round: a missing transition is
  visible, an unwanted one on the fill is not. The spec states it so the next
  person does not "fix" it back to `all`.
- **The test pins rule names, so renaming a control breaks it.** → Intended. A
  rename is exactly when someone should be re-reading this decision, and a test
  that quietly matches nothing is worse than one that fails.
- **`make test` cannot tell you the change worked**, only that the source still
  says what it decided. → Same limitation as the grid-windowing and
  tab-transition tests, and handled the same way: the test pins the decision,
  a human confirms the picture on the `:dev` image before archiving.
