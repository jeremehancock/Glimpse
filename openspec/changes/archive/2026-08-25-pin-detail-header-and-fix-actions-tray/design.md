## Context

Two faults, measured in a real browser over CDP at 390×844 against the running
container. Both are consequences of the tray conversion inheriting CSS written
for the layout it replaced.

**The Actions tray opens empty.** `web/index.html` carries

```css
@media screen and (max-width: 992px) {
    .sort-toggle { display: none; }
}
```

which means "hide the header's sort controls on a narrow screen". The Actions
tray's body *is* a `.sort-toggle` — its only child — so the rule empties the tray
it was never aimed at. Measured with the tray open:

```
panel  y 740 → 844   (103px tall)
  grip                17px   ✓
  head  "Actions"     48px   ✓
  body  y 824 → 844   20px   ← its own bottom padding, nothing else
    └─ .sort-toggle   display: none, height 0
```

A sweep of all four overlays at 390px found this is the only overlay with
CSS-collapsed body content. One rule, not a pattern.

The same rule opens a second hole. `.sort-toggle` hides at ≤992 but
`.mobile-menu-button` only appears at ≤768:

| Width | header sort/genre | hamburger | Result |
| --- | --- | --- | --- |
| 1280 | shown | hidden | fine |
| 1000 | shown | hidden | fine |
| **900** | **hidden** | **hidden** | **no sort, genre or server switch** |
| **800** | **hidden** | **hidden** | same |
| 700 | hidden | shown | tray (empty — the fault above) |

**The detail tray's regions are wrong.** Measured with the detail open:

```
                                    y
  ┌───────────────────────────┐   195  ← panel top
  │ ▓▓▓▓▓▓ ═══ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │   196  grip — handle sits ON the art
  │ ▓▓▓▓ Title            ×   │   213  .modal__head
  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │   274  ┐
  │ ▓▓▓▓ ┌────┐              │        │
  │ ▓▓▓▓ │post│ 2023         │        │  .modal-header
  │ ▓▓▓▓ │ er │ PG-13 120min │        │  ← INSIDE the scroller
  │ ▓▓▓▓ └────┘ [Trailer]    │        │
  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │   476  ┘ ← art ends (fixed 280px)
  │      Overview            │   498  ┐
  │      Genres              │   575  │  .modal__body scrolls
  │      Cast                │   659  │
  │      Date added          │   754  ┘
  └───────────────────────────┘   844
```

`.modal-backdrop-art` is `top: 0; height: 280px` on the panel. The 280px was
sized for the *desktop dialog*, where the identity block is about that tall; on
the tray it overshoots 214px past the head into the scrolling body, so content
slides beneath a stationary image. And `.modal-header` is the first child of the
scroller, so the poster scrolls away with the summary.

## Goals / Non-Goals

**Goals:**

- Every control the Actions tray carries is reachable at every viewport width.
- The detail overlay has one explicit fixed region and one scrolling region, the
  same at every width.
- The item's artwork never runs under the grab handle and never extends into
  scrolling content.
- A drag on the fixed region dismisses, so the pinned block does not read as a
  dead zone.

**Non-Goals:**

- A full audit of `index.html`'s breakpoint spread (992 / 768 / 767 / 600 / 480)
  against the overlay system's 767/768. Real, and larger than this; the user
  chose to close the dead zone rather than reconcile everything.
- Splitting `index.html` into ES modules. That is the separate planned change and
  it will move this CSS wholesale.
- Renaming `.sort-toggle`. The name is now wrong — the tray's block holds Genre,
  Switch server and Install App too — but a rename touches every rule and every
  `querySelectorAll('.sort-button')` call site for no behavioral gain.
- Changing what the detail overlay *shows*. Only which parts of it hold still.

## Decisions

### Scope the hide rule to the header; bring the hamburger up to meet it

```css
@media screen and (max-width: 992px) {
    .header-content .sort-toggle { display: none; }
    .mobile-menu-button { display: flex; order: 3; }
}
```

Two edits, and they do different jobs. The descendant selector stops the rule
reaching overlay content, which is the emptying fault. Raising the hamburger's
breakpoint from 768 to 992 closes the dead zone, by making the hand-off exact at
the width the header controls actually withdraw.

**The breakpoint moves up, not down, and that is measured rather than assumed.**
The obvious reading — hide the header copy later, at 767, so it survives until
the hamburger arrives — does not survive contact with the layout. With the hide
rule removed, the tabs row overflows `.header-content`'s right edge at ≤850px and
the search container collapses to 54px from 992px down. The ≤992 rule exists for
a real reason: logo + search + two tabs + four sort controls do not fit below
about 992px. So the page copy has to keep withdrawing there, and it is the
overlay's trigger that must arrive earlier.

Measured with the hamburger raised to 992: no document overflow and no header
overflow at 1280 / 992 / 900 / 800 / 769 / 768 / 700 / 390, with the search
container at 347px at 992 and 124px at 769.

`.header-content .tabs { display: none }` stays at ≤768. Movies and TV Shows fit
comfortably at 769–992 and are worth keeping in the page; below 768 they give way
to the horizontal swipe, as the Actions tray's own comment records. Between 769
and 992 the tray therefore carries sort, genre, server and install while the tabs
stay in the header — which is coherent, not a compromise.

At those widths `overlays.css` presents a `.sheet` as a centred dialog rather
than a bottom-docked tray (`min-width: 768px`), so the Actions overlay arrives in
the pointer shape on a tablet. That is the existing designed behaviour and needs
no special casing.

**There is no 768/767 off-by-one to fix.** An earlier reading of this design
claimed the header controls and the hamburger were both visible at exactly 768px.
They are not: `.sort-toggle` is nested *inside* `.tabs`, so
`.header-content .tabs { display: none }` at ≤768 already takes the sort controls
with it. `.mobile-menu-button` stays on `max-width: 992px` alone.

*Alternative considered:* give the tray's block a different class. Cleaner
semantically, but it means restyling from scratch a block whose appearance is
currently correct, and it does nothing about the dead zone.

*Alternative considered:* reflow the header at 769–992 so everything fits —
collapse the sort buttons to icons, drop the server text. More work, and it
squeezes the search box, which is the header's primary control.

*Alternative considered:* `.sheet__body .sort-toggle { display: flex }` to
out-specify the hide. This is the pattern that produced the bug in the first
place — a second rule racing the first — and it leaves the unqualified selector
in place to catch the next overlay that reuses the class.

### The fixed region is a real element, not a sticky child

`.modal-header` moves out of `.modal__body` to become its sibling:

```
.modal__panel
  .sheet__grip            ← drag; art fades out beneath it
  .modal-backdrop-art     ← absolute, behind
  .modal__head            ← title + ×; drag region
  .modal-header           ← MOVED: poster/year/meta/actions, fixed
  .modal__body            ← scroller: overview, genres, cast, date
```

`position: sticky` on `.modal-header` inside the scroller would be a smaller
diff, and is wrong here. A sticky element is still *in* the scroller, so
`touch-action: none` on it cannot be honoured — the browser reclaims the drag as
a scroll, silently, which is precisely the trap `test_drag_regions_are_not_the_scroller`
exists to catch. It also leaves the artwork's extent undefined, because there is
no element whose height the art can key to.

Making it a sibling gives the panel three flex children with explicit roles:
`flex: 0 0 auto` for grip, head and identity block; `flex: 1 1 auto; min-height:
0` for the body. The existing `.modal-header` `border-bottom` already draws the
division.

### The pin applies at both widths

One structure, no breakpoint-conditional DOM semantics — the house style. It does
change the desktop dialog's appearance: the poster no longer scrolls away. The
panel is `max-height: 88vh` there with room to spare, so the cost is appearance
only, and having "the fixed region" mean the same thing at every width is worth
more than preserving the current desktop scroll.

### The artwork keeps `top: 0` and is faded out under the grip

A CSS mask, not a change of origin:

```css
mask-image: linear-gradient(to bottom, transparent 0, black <grip-height>);
```

The full-bleed look is preserved — the art still reaches the panel's top edge —
while the handle sits on effectively clean surface. Moving the art's `top` down
instead would leave a hard band of bare surface above it, which reads as a gap
rather than a design.

`-webkit-mask-image` is paired with it. Both are needed for older WebKit, and a
browser honouring neither degrades to today's appearance, which is legible if
imperfect — not a failure.

The fixed 280px height goes. The art's bottom now coincides with the identity
block's bottom. The mechanism follows from the flex layout: the art is absolutely
positioned against the panel, so its height must be driven rather than intrinsic.
Deriving it from the fixed region's measured height in JS would be a resize
observer and a second source of truth for a layout CSS already knows. Instead the
artwork becomes a background layer *of the fixed region itself* — grip, head and
identity block wrapped in one positioned container that the art fills with
`inset: 0`. Then it cannot extend past the fixed region by construction, at any
width, for any content, which is the property the spec asks for.

*Alternative considered:* keep the art as a panel-level absolute layer with
`height` set from a CSS variable the JS writes on open. Works, but reintroduces a
JS-owned layout number that goes stale on rotation and on a late-loading poster.

### The drag gesture opts in to the fixed region

`overlays.js` arms only on `.sheet__grip, .sheet__head, .modal__head`. Once the
identity block is visually part of the fixed top of the tray, a drag on it that
does nothing reads as broken, so the selector gains the wrapper introduced above.

Buttons inside it — the trailer control, the genre chips are elsewhere — keep
working. A tap without movement ends `endDrag` with `dy: 0`, below any threshold,
so nothing is dismissed and the click proceeds normally. `touch-action: none`
suppresses browser panning, not activation.

### Dead CSS goes in the same pass

- `.modal-body` (single-dash) at three places in `index.html`. The markup is
  `.modal__body`; these rules match nothing.
- `.modal-header { margin-top: 40px }` in two media queries — clearance for a
  close `×` that is hidden on touch. 40px of the fixed region's budget for
  nothing.

Removing them is not tidying: both are live-looking rules for the exact elements
this change restructures, and leaving them makes the next reader believe the old
layout is still in play.

## Risks / Trade-offs

- **The fixed region eats a short viewport.** Grip 17 + head 48 + identity block
  184 = 249px today; dropping the dead 40px leaves ~209px. Fine at 844px tall,
  tighter on a 667px device where the panel is 587px. A multi-line title makes it
  worse. → Cap the fixed region with `max-height` in `vh` and let it scroll
  internally past the cap, so the scrolling region can never be squeezed to
  nothing. Covered by a scenario.
- **The desktop dialog's appearance changes** and the user has been looking at
  the phone. → Called out here as a deliberate decision, not a side effect; easy
  to confine to `max-width: 767px` later if it reads badly.
- **Restructuring the panel can break the existing drag-region test.**
  `test_drag_regions_are_not_the_scroller` asserts the head is never an ancestor
  of the body. Wrapping grip + head + identity block in one container puts the
  head one level deeper. → Verify the test still passes and extend it to assert
  the new wrapper is a sibling of `.modal__body`, not an ancestor. If the regex
  no longer matches the markup it must be *fixed*, never relaxed.
- **Runtime code appends into the panel.** `openModal()` appends a date section
  to `.modal .modal__body` and a retry button to `.modal-actions`. Both are
  document-wide queries that survive the move, but they are the kind of thing a
  markup test cannot catch. → Open the detail overlay in a real browser and
  confirm both still land in the right region.
- **A headless check will report this fixed while it is not.**
  `--virtual-time-budget` disables `requestAnimationFrame`, on which Alpine's
  transitions, the scroll lock and the focus manager all sequence, so every
  overlay stays frozen shut. → Verification is over CDP against a real browser at
  1280px *and* 390px, as the handover records.

## Migration Plan

None. No data, no configuration, no container change. The frozen
`docker-compose.yml` surface is untouched: no environment variable is added,
removed or reinterpreted, so `tests/test_compose_surface.py` is unaffected and an
existing user's compose file runs this unchanged.

`make docker-smoke` is not required — nothing under `Dockerfile`, `config/` or
the entrypoint changes. `make lint` and `make test` are.

Rollback is a revert; the change is confined to three authored web files and one
test file.

## Open Questions

1. **Should `.sort-toggle` be renamed?** The block holds Genre, Switch server and
   Install App as well as the two sort buttons, at which point the name describes
   a third of its contents. Deferred here as churn; the ES-module split will move
   this CSS anyway and is the natural moment.
2. **Does the fixed region want a scroll shadow?** A subtle shadow on the
   scroller's top edge signals that content passes beneath the pinned block. Not
   specified — worth judging against the real thing rather than deciding now.
3. Inherited from `convert-overlays-to-trays` and still unanswered: whether the
   detail overlay should be a tray on desktop too. This change pins the identity
   block at both widths, which is orthogonal — but if the answer turns out to be
   "yes, a tray everywhere", it removes the trade-off noted above entirely.
