## Why

Clicking Movies or TV Shows washes the label out: for the length of the state
change the tab's text is near-white on a near-accent fill, which on the Plex
yellow is close to unreadable. The tab is the app's primary navigation and the
one control a user watches while they operate it, so the ugliest moment in the
interface is the moment they are looking at it.

The same wash affects the sort and genre pills, which change state the same way
for the same reason.

## What Changes

- A pill control that switches between the neutral fill and the accent fill
  changes **both together, on the same frame**. Neither the fill nor the label
  is transitioned, so the pill never wears a label that does not belong to it.
- `.tab` states its own resting colour instead of inheriting it, so the rule
  that governs the label is the rule that reads as governing it.
- `transition: all` goes, and with both halves of the pair barred there is
  nothing left for these rules to animate, so they declare no transition at all.
  `all` is what swept `color` into the fade in the first place, and it silently
  enrolls every property added later.
- The hover tint becomes instant, as a consequence: hover and selection share
  one `background-color`, and CSS cannot tell them apart.
- A test pins the shape: no rule that toggles the accent fill may transition
  either half of the pair. CI has no browser, so the source decision is what can
  be guarded.

**An earlier version of this change eased the fill and switched only the label.
It shipped to `:dev` and a user reported the result** — deselecting a tab put a
fully white label on a fully yellow pill for the length of the fade, which is
worse than the defect it replaced. Contrast is a relation between two
properties, not a fact about either, so moving one of them alone only reflects
the bad window. `design.md` records all three orderings and why only "both
together" works.

Out of scope, deliberately:

- Controls that are accent-filled at rest and never cross (`.genre-badge`,
  `.scroll-to-top`, `.roulette-close-btn`) — there is no crossing to wash out.
- `.genre-item.active`, which moves between two light-on-dark colours; every
  midpoint stays legible.
- The other `transition: all` declarations in the stylesheet. They are worth
  tidying and are not this defect; sweeping them in here would make a
  contrast fix indistinguishable from a refactor.

Not breaking. Nothing user-configurable changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `visual-design`: adds a requirement that a control crossing between the
  neutral and accent fills keeps its label legible throughout the change —
  the label colour is switched, never interpolated.

## Impact

- `web/index.html` — the `.tab`, `.sort-button` and `.genre-button` rules in the
  inline stylesheet. CSS only; no markup and no script changes.
- `tests/` — one new test asserting the rule shape.
- **The frozen `docker-compose.yml` surface is untouched.** No environment
  variable is read, added or removed, and an existing user's compose file runs
  this unchanged.
- No `Dockerfile`, `config/` or entrypoint change, so `make docker-smoke` is not
  required by this change.
- Per-server theming is unaffected: the fix is about how the label crosses
  between fills, not about what either fill is, so it holds for the Plex,
  Jellyfin and Emby palettes alike.
