## Context

Four defects found while validating the `:dev` image. They are unrelated in
mechanism but share a shape: each one leaves the app looking correct while
behaving incorrectly, with nothing logged and nothing thrown.

Current state, measured against a container built from `dev` and driven over CDP
at 1280×900 and 390×844:

| Observed | Measured |
| --- | --- |
| Detail dialog under the header | `.header` z-index `100`; `--z-modal` `55`, `--z-sheet` `50` |
| Header lit above every tray backdrop | same |
| Tray sort control does nothing | grid unchanged, `.active` unmoved after tap |
| Tray server control does nothing | `button.onclick === false`, label still the authored placeholder |
| Grab handle dim over artwork | artwork `position:absolute; z-index:0`, grip in flow and unpositioned |
| A fixed desktop bug reported as unfixed | `/assets/` served cache-first from a cache name unchanged all rewrite |

### The layering survey

Every `z-index` under `web/`, excluding the vendored Alpine build, classified.
Recorded here because lowering `.header` exposes any value that was chosen to
beat `100`, and a spot check would not have found one.

| Value | Selector | Where | Class |
| --- | --- | --- | --- |
| `--z-modal` (55) | `.modal` | `overlays.css:133` | overlay |
| `--z-sheet` (50) | `.sheet` | `overlays.css:24` | overlay |
| `1000` | `.scroll-to-top` | `index.html:662` | **chrome — moves** |
| `100` | `.header` | `index.html:227` | **chrome — moves** |
| `90` | `.swipe-indicator` | `index.html:1083` | **chrome — moves** |
| `10` | `.trailer-container iframe` | `index.html:3250` | scoped to `.trailer-container` |
| `5` | `.trailer-loading` | `index.html:3267` | scoped to `.trailer-container` |
| `1` | `.search-clear` | `index.html:364` | scoped to the search field |
| `1` | `.modal-header` | `index.html:800` | scoped to `.modal__fixed` |
| `0` | `.modal-backdrop-art` | `index.html:714` | scoped to `.modal__fixed` |
| `0` | poster placeholder | `index.html:1056` | scoped to a card |

Three chrome elements, seven values that only order siblings inside a positioned
ancestor and never compete with an overlay, and the two overlay tiers themselves.
Nothing else was hiding behind the header's `100`.

Two constraints frame every decision below.

`tokens.css` already declares `--z-chrome: 30` with a comment describing exactly
the ordering that is missing. The token was written and never wired up; this is
not a new scheme, it is finishing one.

Nothing under `web/` is built, bundled or transpiled — nginx serves the files as
authored. So "run this later" has to be expressed in the page's own load order,
not by a bundler's module graph.

## Goals / Non-Goals

**Goals:**

- Page chrome ranks below the overlay scale, read from tokens rather than
  restated per element.
- Every control inside the teleported Actions tray carries its behavior.
- A rebuilt stylesheet or script reaches an installed client, without losing
  offline capability.
- The detail overlay's grab handle is legible over any item's artwork.
- Regression tests that fail if any of the four is undone.

**Non-Goals:**

- Restyling anything. The genre and server items look wrong for a separate
  reason — they became `<button>` elements without CSS following — and that is
  the sibling change, not this one.
- Changing which shape an overlay wears at which width. Verified correct.
- Changing tray motion timing. Measured within ~20ms of Marquee's; the "not
  smooth" report is the chrome-above-backdrop defect, not the durations.
- Reworking the roulette overlay's structure. Sibling change.
- Any new environment variable, or any edit to `docker-compose.yml`.

## Decisions

### 1. Chrome moves down; overlays stay where they are

Move `.header`, `.scroll-to-top` and `.swipe-indicator` onto `--z-chrome`.

**Alternative considered:** raise `--z-sheet` and `--z-modal` above 100. Rejected
— it leaves the ladder undocumented and unbounded. The next fixed element someone
adds picks a number by looking at neighbours, and the neighbour it finds would be
1000. Lowering chrome makes the token comment true and gives the next element an
obvious tier to join.

`.scroll-to-top` at `1000` is the one to watch: it is *not* currently covered by
overlay backdrops either, so this fixes a second instance nobody reported.

A test asserts the ordering from the stylesheet, transcribed rather than derived
— a test that recomputes the ladder from the same file it is checking cannot fail.

### 2. Bind the tray's controls after teleport, not at a fixed later time

The precise failure, confirmed behaviourally: the *binding pass* runs at parse
time and finds only the header's copies, while *runtime* queries reach the
teleported markup fine. Tapping the header's sort control marks all four
`.sort-button` elements active, tray copies included — `setSortMethod` queries at
click time, by which point Alpine has teleported. So only the one-time binding
passes are broken:

```
parse time    inline <script> runs
              querySelectorAll('.sort-button')          → header only  ✗ binding
              renderServerSwitcher()                    → header only  ✗ binding
                                                          tray is still <template>
      defer   alpine.min.js boots, x-teleport moves the tray into <body>
   any tap    setSortMethod() → querySelectorAll(...)   → all four     ✓ runtime
```

**Decision:** run the binding passes from Alpine's `alpine:initialized` event.
That is the documented point at which teleports have been performed, and it names
the actual dependency — "after the overlay markup exists" — rather than a delay
chosen to be long enough.

**Alternatives considered:**

- *`DOMContentLoaded`.* Wrong dependency and wrong order: the Alpine script is
  `defer`, so it executes around the same point, and the relative order is not
  something to rely on.
- *`setTimeout(…, 0)`.* Works by accident today. It encodes no dependency, so it
  breaks silently the day Alpine's boot moves behind another microtask — and the
  symptom is this same bug, which took a CDP session to distinguish from a
  styling problem.
- *Event delegation from `document`.* Genuinely robust and would end this class
  of bug outright. Rejected for scope: it is a rewrite of how every control in
  the page is wired, and this change should be small enough to validate quickly
  against three blocked changes. Worth revisiting on its own.
- *Untangle the teleport.* Rejected — `CLAUDE.md` records why the tray is
  teleported (`backdrop-filter` on the header makes it a containing block for
  fixed descendants), and the note explicitly warns against "simplifying" it back.

**Guard against recurrence:** the binding passes must be idempotent, because
`renderServerSwitcher()` is already called again on a server change. It assigns
`button.onclick =` rather than adding a listener, so it is; the sort pass uses
`addEventListener` and will need a marker attribute or a move to `onclick` to
stay safe if it is ever run twice.

### 3. Static assets go network-first with cache fallback

Reuse `networkFirstWithCacheFallback()`, which `sw.js` already applies to the app
shell. Same function, extended to same-origin `/assets/`.

**Alternatives considered:**

- *Bump `CACHE_NAME` every release.* Manual, forgettable, and it was already
  forgotten for the whole rewrite. It also does nothing for a user mid-release.
- *Stale-while-revalidate.* Serves one stale load after each upgrade. Acceptable
  in production, but during active development it means every validation pass
  shows the previous build — the exact failure being fixed.
- *Version the asset URLs.* Requires generating markup or a build step. `web/` is
  served as authored, and the entrypoint generates exactly two files by rule.

Offline is unaffected: the assets stay in `STATIC_ASSETS` and are still precached
on install, so a failed fetch falls back to the cache. `alpine.min.js` in
particular is vendored precisely so the app survives offline, and it stays
precached.

**Found during implementation — the strategy change alone is not enough.** There
are three caching layers, not two, and all three had to agree:

```
 1. service worker cache   cache-first  →  network-first          (sw.js)
 2. browser HTTP cache     max-age 7d   →  no-cache, revalidate   (nginx.conf)
 3. sw.js itself           max-age 7d   →  no-cache, revalidate   (nginx.conf)
```

Layer 2 is the one that hides: `networkFirstWithCacheFallback()` calls plain
`fetch()`, which consults the HTTP cache, so nginx's `max-age=604800` on
`\.(css|js|…)$` satisfied the "network" fetch from disk. The service worker was
behaving correctly and still serving week-old CSS.

Layer 3 is worse and was invisible until measured. The same extension regex
matched `/sw.js`, so the worker that decides the caching policy was itself held
for a week — meaning a policy fix could not deploy itself. Both get exact-match
and `^~` locations that outrank the regex.

These filenames carry no content hash and never will: nothing under `web/` is
built or bundled, so a changed file keeps its URL. `no-cache` means revalidate,
not "do not store" — nginx answers 304 from the ETag, so correctness costs one
conditional request. `/images/` and `/data/` keep their 7-day cache; they are
genuinely static.

`CACHE_NAME` is bumped once to evict entries already poisoned. The existing
activate handler deletes caches whose name does not match, so nothing new is
needed to clean up.

### 4. The grab handle is lifted *and* the artwork cleared behind it

Both halves, because either alone leaves a defect:

- Lift alone → a grey handle sits on an arbitrary photograph. Legibility becomes
  a property of which item was opened.
- Clear alone → paint order still puts the positioned artwork above the
  unpositioned grip, so the fade is the only thing holding the line, and it is
  the thing that was already miscalibrated.

The current mask runs `transparent 0 → opaque at var(--grip-height)`, and
`--grip-height` is `17px` = 12px grip padding + 5px handle. That is the handle's
*lower* edge, so the handle sits in the 71–100% opaque tail. The fade must clear
the handle and then some.

The token stays the single source for the grip's metrics — `CLAUDE.md` records
that two hardcoded `17`s would drift and that the symptom would be an illegible
handle on bright artwork only. The margin below the handle is expressed relative
to the token, not as a second literal.

## Risks / Trade-offs

- **Lowering `.header` exposes an ordering the header currently masks.** Other
  page elements may have been given numbers chosen to beat `100`. → Grep every
  `z-index` in `web/` as an explicit task, not as a spot check, and record the
  full ladder in the test.

- **Network-first costs a round trip per asset on every load.** → Negligible for
  a self-hosted LAN app, and it is already the app shell's cost. Offline is
  covered by the fallback, which is the branch that matters.

- **`alpine:initialized` ties page wiring to Alpine's lifecycle.** A control that
  works today only because it was bound early could break. → The passes being
  moved are those that must see the teleported markup; the rest stay put. Test
  both copies of every moved control.

- **`sw.js` ships in the image and CI builds the image only after the push.** →
  `make docker-smoke` locally before pushing, per `docs/docker.md`.

- **A service worker fix cannot fix the client that has the bad service worker
  ...** for the current load. The new worker installs, `skipWaiting()` and
  `clients.claim()` are already in place, and the cache-name change evicts on
  activate — so it self-heals on the next load, not this one. → Validate on a
  fresh profile, and expect one stale load on an existing one.

- **The three blocked changes are each waiting on `:dev` validation.** Landing
  this without the sibling restyle means validating against controls that work
  but still look wrong. → Expected; say so when asking for validation, so
  cosmetic findings are not re-reported as defects.

## Migration Plan

No data migration and no configuration change. Deployment is the ordinary image
rebuild.

On a user's first load after upgrade the service worker activates, deletes the
previous cache, and re-fetches the app's CSS and JS once. Nothing is asked of
them, and a client that is offline at that moment keeps the precached copies.

Rollback is reverting the commit and rebuilding. The cache-name bump is not
reversible in a meaningful sense — rolling back leaves clients on the new name —
but a rollback would restore the old cache-first behavior against the old assets,
which is self-consistent.

## Open Questions

- Should the sort pass move from `addEventListener` to `onclick =` for
  idempotence, matching `renderServerSwitcher()`? Leaning yes: it makes "run this
  again" safe by construction rather than by a marker attribute nobody will
  remember to check.
- Event delegation from `document` would end this whole class of bug. Out of
  scope here — worth its own change once the three blocked ones have landed?
