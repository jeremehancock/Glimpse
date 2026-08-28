## Context

The detail overlay's scrolling body (`.modal__body`) holds four sections, each a
`.modal-section-title` heading over its content:

| Section | Content | Source |
| --- | --- | --- |
| Overview | the summary, bare prose | markup |
| Genres | `.genre-tag` pills in a flex row | markup |
| Cast | `.cast-item` cards in a grid | markup |
| Date Added | one line of bare prose | appended by `openModal()` |

Three rules set every gap between them:

```css
.modal-section       { margin-bottom: 5px; }
.modal-section-title { font-size: 1.3em; margin-bottom: 15px; }
.summary-section     { line-height: 1.7; color: var(--light-text); }
```

**The rhythm is inverted.** A heading stands 15px from its own content and 5px
from the block above it, so every heading groups with the section it does not
belong to. This is the whole of the reported defect; everything below is why the
gaps are also unequal.

**The gaps are three different sizes, and none of them is 5px.** The distance
the eye reads is not the margin. Bare text is measured to the glyph, so its
half-leading — `(line-height − 1) ÷ 2` of the font size — is part of every gap
touching it. A filled object (a genre pill, a cast card) is measured to its
edge, and has no half-leading to add. At the 16px base and the inherited 1.5
leading:

| Gap | Arithmetic | Reads as |
| --- | --- | --- |
| summary → "Genres" | 5.6 + 5 + 5.2 | **15.8px** |
| pills → "Cast" | 5 + 5.2 | **10.2px** |
| cards → "Date Added" | 5 + 5.2 | **10.2px** |
| "Overview" → summary | 7.28 + 15 + 5.6 | **27.9px** |
| "Genres" → pills | 5.2 + 15 | **20.2px** |
| "Cast" → cards | 5.2 + 15 | **20.2px** |
| "Date Added" → date | 5.2 + 15 + 4 | **24.2px** |

Two separate causes are visible in that table.

**`.summary-section` sets leading for a block that contains a heading.**
`line-height: 1.7` is inherited by the "Overview" heading, whose half-leading is
therefore 7.28px against the other three headings' 5.2px. That is why "Overview"
alone sits ~2px lower and stands ~5px further from its own text — and it is the
same half-leading trap already recorded for `.sheet__title` in overlays.css,
reached from the other direction: there a heading's leading was the number
nobody checked, here it is a number nobody *set*.

**A section ending in prose and a section ending in a box do not leave the same
gap even when their margins are identical.** 15.8px against 10.2px above, from
one shared `margin-bottom: 5px`.

The measurements above are computed from the CSS, not read off a browser; the
implementation verifies them in DevTools.

## Goals / Non-Goals

**Goals:**

- One separation between sections, stated once, and every section separated by
  it — regardless of whether the section above ends in text or in a filled box.
- A heading closer to what it introduces than to what precedes it, by a margin
  large enough to read as grouping rather than as a rounding difference.
- The first heading clears the division under the poster block by that same
  separation. The border is the strongest break in the body and must not be its
  smallest gap.
- A heading's position determined by the rule that sets a heading's type, never
  by leading a section set for its prose.

**Non-Goals:**

- A general spacing scale in `tokens.css`. One value crosses a file boundary here
  and that one is tokenised; inventing a `--space-1..6` ramp with a single
  reader each is the "token with no reader" this repo has already deleted once.
- Any change to the fixed region — the poster, the identity block, the head, the
  artwork, the division border itself. Those were settled by
  `pin-detail-header-and-fix-actions-tray` and `improve-detail-overlay-legibility`
  and are not reopened.
- Any change to the other overlays' bodies. They hold one block each and have no
  internal rhythm to state.
- Type changes. No font size, weight or colour moves. `line-height` on the
  heading is set because it is currently unset, not to restyle it.

## Decisions

### The separation is one token; the heading gap is half of it, in `calc()`

`--overlay-section-gap: 24px` in `tokens.css`, read by `.modal__fixed +
.modal__body` in `overlays.css` and by `.modal-section + .modal-section` in
`index.html`. Two rules in two files have to agree about this number, which is
exactly the condition `tokens.css` states for itself.

The heading gap is written `calc(var(--overlay-section-gap) / 2)` rather than as
a second token holding `12px`. The relation *is* the decision — a heading groups
downward because its own gap is half the gap around it — so it belongs in the
code, where changing the token moves both halves together and cannot leave a
build where a heading sits equidistant between two sections.

*Alternative considered: two tokens (`--overlay-section-gap`,
`--overlay-heading-gap`).* Rejected: the second has exactly one reader, and a
token whose value can be edited independently is precisely how the relation gets
broken silently.

*Alternative considered: keep the numbers literal in both files.* Rejected: this
repo has already shipped a pair of numbers that were meant to agree and drifted
(the 992px/768px affordance pair, and the 14px/16px head padding pair).

### Separation is `margin-top` on the following section, not `margin-bottom`

`.modal-section + .modal-section { margin-top: … }`, and the bare
`.modal-section { margin-bottom: 5px }` rule is deleted.

A trailing `margin-bottom` on every section adds itself to the body's own
`padding-bottom`, so the space under the last section is a number nobody chose —
25px today against a 20px inset at the sides. Stating the gap *between* siblings
means the body's padding is the body's padding.

The Date Added section is appended by `openModal()` at runtime, and an adjacent
sibling selector matches it the moment it is inserted — no class to remember, no
registry.

### The first heading clears the division by the same separation

`.modal__fixed + .modal__body { padding-top: var(--overlay-section-gap) }`,
replacing a literal `20px`.

That 20px was chosen to match the body's horizontal inset — a real reason, and
the wrong one now that the body has a stated vertical rhythm. The border under
the identity block is a heavier divider than the whitespace between two sections,
so it cannot be the smaller gap. One rule with no exception: **a heading stands
one separation clear of whatever precedes it**, whether that is another section
or the division.

The selector stays keyed on `.modal__fixed` rather than on the detail overlay.
That was deliberate when the rule was written and nothing here changes it.

### A heading states its own leading

`.modal-section-title` gains `line-height: 1.3`.

`1.3` rather than restating the inherited `1.5` because a heading here is one to
two lines and does not want prose leading; the tighter value also puts less
uncheckable half-leading (3.12px) inside gaps whose whole point is being equal.
The unitless form scales with the `1.1em` override at ≤600px.

This is the `visual-design` requirement *"A rule that appears to set an element's
type must set it"* applied forward instead of retroactively: `.modal-section-title`
already sets the family's size, weight and colour, so leaving leading to whatever
an ancestor happens to say is the gap through which `.summary-section`'s `1.7`
arrived.

### Prose trims its own half-leading, and derives the trim from its own leading

A shared class for bare text inside the body:

```css
.modal-prose {
    --prose-leading: 1.7;
    line-height: var(--prose-leading);
    margin-block: calc((1 - var(--prose-leading)) * 0.5em);
}
```

The negative margin is exactly the half-leading the line box adds above and
below the glyphs — `-0.35em`, 5.6px at 16px — so the declared gap and the gap
the eye reads are the same number, and a section ending in prose leaves the same
space as one ending in a pill or a card.

The trim is computed from `--prose-leading` rather than written as `-0.35em`
because the two must never disagree. A literal is a second copy of the leading,
and the failure mode when it drifts is silent: the gaps look almost right.

**It works by margin collapsing, which is the part to verify rather than assume.**
Each usage collapses as follows:

- *Between the heading and the prose.* The heading's `margin-bottom` (12px) and
  the prose's `margin-top` (−5.6px) are adjacent siblings, so they collapse to
  `12 + (−5.6) = 6.4px`, and the optical gap is `3.12 + 6.4 + 5.6 = 15.12px` —
  equal to the `3.12 + 12 = 15.12px` from a heading to a pill or a card.
- *Between a prose-ended section and the next.* `.modal-section` has no padding
  or border, so the prose's `−5.6px` collapses out to the section's own bottom
  margin, then collapses with the next section's `+24px` to `18.4px`. Optical:
  `5.6 + 18.4 + 3.12 = 27.12px` — equal to the `24 + 3.12 = 27.12px` after a
  pill row or a cast grid.
- *At the foot of the body.* `.modal__body` has `padding-bottom` and is a block
  formatting context (`overflow-y: auto`), so nothing collapses through it. The
  last section's `−5.6px` pulls the content edge up to the final glyph, leaving
  exactly the body's own 20px below it.
- *Inside `.genres-list` and `.cast-grid`.* The no-genres and no-cast fallbacks
  are the sole child of a flex and a grid container respectively, where margins
  do not collapse at all — the negative margin instead shrinks the container to
  the glyph box directly, giving the same result by a different mechanism.

So `.modal-section` must never gain padding, a border, or its own formatting
context, or the trim stops collapsing and every prose gap silently grows 5.6px.
The test pins the derivation; the comment at the rule states the dependence.

*Alternative considered: leave the leading variance alone.* It fixes the
inversion and leaves gaps that differ by 5.6px on 24px — a quarter. This repo
has spent a whole change on a 2px difference between two overlay heads, for the
stated reason that adjacent things not sitting still reads as the app being
loose rather than as a measurement.

*Alternative considered: drop the summary to the same 1.5 leading as everything
else, so there is nothing to trim.* Rejected: 1.7 is a deliberate reading choice
for the one long paragraph in the app, and the user's ask is explicitly that it
feel comfortable to read.

*Alternative considered: `text-box-trim`.* This is what the property is for, and
it is too new to rely on in a PWA that must work on whatever browser a phone
came with.

### `.summary-section` is deleted, class and all

Once `line-height` moves to the prose, the rule holds only
`color: var(--light-text)`, which restates what `body` already sets. An empty
rule and a class with no rule are both the shape of dead code this repo removes
on sight, and `grep` confirms nothing else — no JS, no test, no other stylesheet
— refers to it.

### The prose class is applied at all four sites, including the generated ones

`#modal-summary` and the Date Added value in the markup and in `openModal()`,
plus the two fallback strings `openModal()` writes when an item has no genres or
no cast. Those fallbacks are bare prose in a slot that normally holds boxes, so
without the class they are the one case where the rhythm goes back to being
uneven — rare, which is exactly why it would never be reported.

## Risks / Trade-offs

- **Margin collapsing is subtle and the failure is quiet.** A future
  `overflow`, `display: flex`, padding or border on `.modal-section` stops the
  trim collapsing and adds 5.6px to every prose gap — a change that looks
  unrelated to spacing. → The rule carries a comment saying what it depends on,
  the test pins the derivation, and the browser check in the tasks measures the
  seams rather than reading the CSS.
- **The computed pixel values in this document are arithmetic, not
  measurements.** Font metrics and rounding can move them a fraction. → The
  implementation measures the four heading gaps and three section gaps in
  DevTools before the change is called done; the requirement is that they are
  equal to each other, not that they equal 15.12 and 27.12.
- **`make test` cannot see any of this.** CI has no browser, and a test that
  asserts the CSS says what the CSS says passes whatever it renders as. → The
  test pins *relations* that would otherwise drift — the token has both readers,
  the heading gap is derived from the section gap, the trim is derived from the
  leading — and the pixels are verified by hand, the same split as
  `test_grid_windowing.py` and `tools/grid_metrics.py`.
- **Changing `.modal__fixed + .modal__body` touches a rule shared with any
  future overlay that pins a region.** → Only the detail overlay matches today,
  and the rule's condition is unchanged; only its value now comes from the token.
- **The gaps do not shrink at ≤600px.** A phone gets the same 24px/12px rhythm
  as a desktop. → Deliberate: the body is a single column at every width, so the
  reading rhythm is the same problem at both. Introducing a breakpoint here
  would create the paired-media-query drift this repo has already shipped twice.

## Migration Plan

None. Presentation-only, no persisted state, no config, no data. Rollback is
reverting the commit.

## Open Questions

None.
