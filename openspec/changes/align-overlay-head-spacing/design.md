## Context

Measured with `tools/browser.py` against a running container, at 390×844 (touch)
and 1280×900 (pointer). All five overlays opened at once by setting the Alpine
flags, then measured after a frame.

Distance from the bottom of the grab handle to the first glyph of the title —
i.e. the line box top plus half-leading:

| Overlay | Head rule | `padding-top` | `line-height` | Half-leading | **Glyph gap** |
| --- | --- | --- | --- | --- | --- |
| Actions | `.sheet__head` | 14px | 26.4px | 4.4px | **18.4px** |
| Genre | `.sheet__head` | 14px | 26.4px | 4.4px | **18.4px** |
| Switch server | `.sheet__head` | 14px | 26.4px | 4.4px | **18.4px** |
| Detail | `.modal__head` | 16px | 19.36px | 0.88px | **16.88px** |
| Roulette | `.modal__head` | 16px | 26.4px | 4.4px | **20.4px** |

Titles are `1.1rem` = 17.6px everywhere; `26.4px` is the body's inherited `1.5`,
`19.36px` is `.modal-title { line-height: 1.1 }`.

The same measurement at 1280px, where every grip is hidden and the distance runs
from the panel's top edge instead:

| Overlay | `padding-top` | Border | Flex centring vs the 36px × | **Glyph gap** |
| --- | --- | --- | --- | --- |
| Actions / Genre / Server | 18px | 1px | +4.8px | **28.2px** |
| Detail | 16px | 1px | +8.32px | **26.21px** |
| Roulette | 16px | 1px | +4.8px | **26.2px** |

Two facts fall out of the pointer-width numbers that matter for the fix:

1. `.sheet__head` bumps to `18px` at ≥768px, with a comment explaining that the
   title needs the panel's own top padding once the handle is gone.
   `.modal__head` has no such bump, though its handle is hidden by the very same
   breakpoint — so the compensation exists for one shape and not the other.
2. The title is vertically centred against the 36px close button at pointer
   widths, so padding is not the only term. It is still the only term that
   differs between overlays, because every head holds the same button.

The trailer is the one overlay with a `.modal__head` and **no** grip in its
markup at any width. It is why the pointer-width bump cannot simply be moved to
the base `.modal__head` rule.

## Goals / Non-Goals

**Goals:**

- One glyph gap below the handle, across every overlay, at every width.
- The invariant enforced by a test rather than by a comment.
- `.modal-title` left stating only what it controls.

**Non-Goals:**

- Changing horizontal padding. `.sheet__head` at 16px matches `.sheet__body`;
  `.modal__head` at 20px matches `.modal__body`. Each head is inset with its own
  body, and that is correct.
- Changing the grip's own geometry, `--grip-height`, `--grip-clear`, or the
  artwork mask that reads them.
- Restyling titles. Font size, weight and colour end up exactly where
  `.modal__head h2` and `.sheet__title` already put them.
- Any markup, JavaScript, or behavior change.

## Decisions

### Unify on 14px, not 16px

The tray is the shape the handle exists for, so the tray's spacing is the
reference. Three of the five grip-bearing overlays already use it, which also
makes it the smallest visual change: two overlays move instead of three.

Result on touch: **18.4px** for every overlay, unchanged from what the three
trays show today.

*Alternative — unify on 16px.* Would move all three trays and leave the
roulette alone. Same consistency, more movement, and it would set the reference
by the shape that borrowed the handle rather than the one that owns it.

*Alternative — a `--head-pad-top` token.* Rejected as a token for one consumer
pair in one file. `--grip-height` is a token because a hand-copied value drifted
between a stylesheet and a mask in a different file; these two rules sit twelve
lines apart in `overlays.css` and will be joined into one selector list, so
there is nothing left to drift.

### Give the two heads one selector list for their vertical box

`.sheet__head` and `.modal__head` differ only in horizontal padding once the top
value is unified — same `flex`, `display`, `align-items`, `justify-content`,
`gap`, `border-bottom`, `margin-bottom`, `touch-action`. Writing the shared box
once and the inset per shape makes the divergence structurally impossible rather
than merely corrected. It is also the honest statement of the design: one head,
two insets.

### Key the pointer-width bump to a preceding grip

The bump compensates for a handle that is no longer there, so it belongs to
heads that have a handle. Expressed with the general sibling combinator:

```css
@media (min-width: 768px) {
    .sheet__grip ~ .sheet__head,
    .sheet__grip ~ .modal__head { padding-top: 18px; }
}
```

`~` and not `+`: the detail overlay's grip and head are separated by
`.modal-backdrop-art`, so the adjacent combinator misses exactly the overlay
that most needs to match.

This is also why the bump cannot move to the base `.modal__head`: that would
push the trailer's title down 4px at pointer widths to compensate for a handle
it has never had. With the sibling selector the trailer takes the shared base at
every width and the bump never reaches it.

**The trailer does still move, by 2px, and an earlier draft of this document
said it would not.** That was wrong and the two halves of it contradicted each
other: unifying the shared head on 14px necessarily changes what the trailer
inherits, because 16px was its old value. Measured, the trailer's title goes
from 26.2px to 24.2px below the panel top, at both widths. Accepted rather than
special-cased — a `.modal__head` that opts out of the shared padding is the
divergence this change exists to remove, reintroduced under a different name.

*Note the limit.* A sibling selector matches a grip that is `display: none`,
which is why the rule must still live inside the media query. It selects "has a
grip in the markup", not "has a visible grip". The media query supplies the
second half, and it is the same breakpoint that hides the grip — the pairing the
stylesheet's existing comment insists on keeping together.

### Remove `.modal-title`'s type declarations rather than editing one line

```css
.modal-title {
    margin: 0 0 10px 0;   /* outranked by .modal__head h2 { margin: 0 } */
    font-size: 2.2em;     /* outranked by .modal__head h2 { font-size: 1.1rem } */
    color: var(--light-text);  /* the inherited value; a no-op */
    font-weight: 700;     /* outranked by .modal__head h2 { font-weight: 600 } */
    line-height: 1.1;     /* the only live declaration — and the defect */
}
```

`.modal__head h2` is `(0,1,1)`; `.modal-title` is `(0,1,0)`. The class loses
every collision. Deleting `line-height` alone would leave four declarations that
look like they define the detail title and define nothing — the exact shape that
let an unwanted `line-height` sit unnoticed inside an authoritative-looking rule.
The two media-query overrides (`font-size: 1.5em` at ≤768px, `1.4em` at ≤480px)
are `(0,1,0)` as well and equally dead; they go with it.

The whole rule can be deleted. `.modal__fixed .modal-title`'s line clamp is a
separate rule and stays.

### Verify with the browser, not only with the suite

The suite can pin the source — equal padding, no `line-height` override — and
that is what stops a regression. It cannot confirm the rendered result, because
the measurement includes half-leading and flex centring against a 36px button.
The change is verified by re-running the measurement at both widths and
confirming a single number per width.

## Risks / Trade-offs

**A wrapped detail title makes `.modal__fixed` taller.** Restoring
`line-height: 1.5` takes each line of the detail title from 19.36px to 26.4px.
Clamped at 3 lines that is 79.2px instead of 58.08px — up to 21px more in the
region that must not scroll. → Measured at 390×844 and it does not reach the
body: `.modal__fixed` goes 265.8px → 318.5px while `.modal__body` holds at
189.8px, because the panel sits at 509px against an 88vh (742px) cap and the
extra height comes out of that slack. Even pinned at the cap the body would keep
424px. `overflow` stays `visible` and `scrollHeight == clientHeight`, so the
region is still bounded by the clamp and not by a scrollbar. The clamp stays at
3 lines. Should this ever bind, reduce the clamp — never add `overflow` to
`.modal__fixed`.

**The sibling selector silently stops matching if the grip moves.** Nesting the
grip inside another element, or moving it after the head, drops the bump with no
error — the title simply sits 4px high at pointer widths. → `test_overlay_markup`
already asserts every tray carries a grip; the new padding test asserts the
bump's selector names both heads. Neither catches a grip that has been re-nested,
so the rule carries a comment saying it depends on the grip being a sibling.

**Deleting `.modal-title` relies on the specificity reading being right.** If any
of those declarations is live somewhere unexamined, the detail title changes
size. → `.modal-title` appears in the markup exactly once, inside
`.modal__head`, so `.modal__head h2` matches wherever `.modal-title` does. The
task list re-greps before deleting and the browser measurement confirms the
rendered `font-size` is still 17.6px afterwards.

**Three trays' titles do not move; two do.** The detail title drops ~1.5px, the
roulette title rises ~2px. → Sub-pixel-scale motion on two overlays, in exchange
for the set being uniform. That is the change.

## Open Questions

None. The measurements are taken and the specificity is resolved; the only thing
left to confirm is the 3-line detail title at 390px, which is a task rather than
a question.
