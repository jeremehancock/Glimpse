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
  changes its label colour **instantly**. The fill still eases; the text does
  not, so the label is legible at every point in the change.
- `.tab` states its own resting colour instead of inheriting it, so the rule
  that governs the label is the rule that reads as governing it.
- `transition: all` is replaced on these three controls with the properties
  they actually animate. `all` is what swept `color` into the fade in the first
  place, and it silently enrolls every property added later.
- A test pins the shape: no rule that toggles the accent fill may transition
  `color`. CI has no browser, so the source decision is what can be guarded.

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
