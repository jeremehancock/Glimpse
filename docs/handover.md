# Handover — the rewrite, as of 2026-08-25

Glimpse is mid-rewrite, modelled on [Marquee](https://github.com/jeremehancock/Marquee).
All work is on **`dev`**. **Nothing goes to `main` until the rewrite is
finished.**

This file is a snapshot, not a specification. The specs are in `openspec/`; this
is here so the next session does not have to reconstruct the situation from git
log. Delete it when the rewrite lands.

---

## Where things stand

`dev` is six commits ahead of `main`:

| Commit | What |
| --- | --- |
| `24c50e0` | Spec-driven workflow, quality gates, CI + publish pipeline |
| `8274bda` | **`replace-boot-time-html-rewriting`** — entrypoint 1,915 → 127 lines |
| `2633530` | README title fix |
| `2aa387d` | **`convert-overlays-to-trays`** — six overlays onto one system |
| `c2c2b2e` | Five regressions from the tray conversion |

`make check` is green (157 tests). CI is green on `dev`.

> **As of 2026-08-25, every change in flight is code-complete and the only task
> left in each is ":dev validation".** `cache-for-speed-not-for-offline` was
> applied that evening and is committed with this note; the two before it —
> `fix-overlay-layering-and-dead-tray-controls` (44/45) and
> `restyle-tray-controls` (37/38) — were committed earlier the same day.
> Nothing has been archived, because archiving rewrites `openspec/specs/` and
> the user has not yet validated an image.
> The six-item punch list at the end of this file is what the user wants
> finished before any of it reaches `main`; item 4 is now done.
>
> **`make lint` needs Node 18+.** The shell default here is v16.20.1, which fails
> ESLint 9 with a `structuredClone is not defined` *config* error — not a lint
> error, so it is easy to misread. Use
> `export PATH="$HOME/.nvm/versions/node/v18.20.8/bin:$PATH"`.

### Six OpenSpec changes are implemented but NOT archived

```bash
openspec list
```

Every one of them is code-complete. The outstanding task in each is the same
task: validate the `:dev` image. Nothing may be archived until that happens,
because archiving rewrites `openspec/specs/` — which is still empty, since no
change in this repo has ever been archived.

- **`cache-for-speed-not-for-offline`** — 37/38. Only "validate `:dev`"
  remains. Formerly `serve-the-library-offline`; see item 4 of the punch list
  for why it changed direction.
- **`fix-overlay-layering-and-dead-tray-controls`** — 44/45.
- **`restyle-tray-controls`** — 37/38.
- **`replace-boot-time-html-rewriting`** — 50/51. Only "validate `:dev`" remains.
- **`convert-overlays-to-trays`** — 42/44. Reduced motion and real touch/swipe
  feel still need a physical device.
- **`pin-detail-header-and-fix-actions-tray`** — 27/28, and **the user has
  reported that visual issues remain**. See below before treating it as done.

  It fixes the Actions overlay opening empty on a phone, closes the 769–992px
  band where a tablet had no sort, genre filter or server switch, and gives the
  detail overlay a pinned region so the poster stays in view while the summary
  scrolls. Two faults it uncovered along the way are worth knowing about:
  the overlay's controls were laid out as a horizontal row and ran off the panel
  (invisible for as long as the block was hidden), and the header genuinely
  cannot fit its sort controls below ~992px — which is why the hamburger moved
  **up** to 992 rather than the hide rule moving down to 767.

**Do not archive any of them until the user has validated a `:dev` image.**
Archiving rewrites `openspec/specs/`, which becomes the source of truth.

### `pin-detail-header-and-fix-actions-tray` is NOT finished

On 2026-08-24 the user reviewed it and said *"that is better, but I still see
some issues"*, then cleared context to describe them in a fresh session. **They
have not been described yet.**

So: do not read 27/28 as "one physical-device check away from done". **Ask what
the remaining issues are before changing anything.** Guessing from the diff will
produce work the user did not ask for, and the two faults this change already
uncovered by accident are evidence that this area has more in it than the
markup shows.

The unchecked task 9.1 is a genuine physical-device check (drag feel and handle
contrast in daylight) and is separate from whatever the user is seeing.

---

## What is done

**The container no longer rewrites its own HTML.** `config/entrypoint.sh` went
from 1,915 lines and ~80 `sed` substitutions to 127 lines that generate
`config.json`, `manifest.json` and the crontab and touch nothing else. The
`/plex/`, `/jellyfin/` and `/emby/` routes are nginx aliases over one
`index.html` rather than four copies of it.

**Every overlay uses one system.** `.sheet` (tray) and `.modal` (dialog), with
`.modal--tray-on-touch` for a dialog that becomes a tray on a phone. Alpine —
vendored, no build step — owns open state; `web/assets/overlays.css` owns
appearance; `web/assets/overlays.js` owns the drag gesture, the page scroll lock
and focus management. The genre filter, which used to be a desktop dropdown *and*
a separate phone drawer, is now one implementation.

---

## What is left

1. **Hear out the user's remaining issues** with
   `pin-detail-header-and-fix-actions-tray` — see above. They exist and have not
   been described.
2. **Validate `:dev`** — the gate on everything else. See "Building `:dev`".
3. **Split `web/index.html` into ES modules.** The planned change, not yet
   proposed. `index.html` is still ~4,000 lines and carries a temporary config
   adapter, marked in-file with the change name that should remove it.
4. **Regenerate the screenshots in `assets/`.** All six predate the rewrite —
   `screenshot-details-*` in particular show the detail view as a centred box
   with a corner close button, which is the presentation the tray conversion
   replaced. They are served from `main`, so they will not look wrong to anyone
   until the rewrite merges, and then all six will at once. This needs a real
   media library, so it is a release-time task rather than a per-change one.
5. **Then** archive all six changes, bump `VERSION` past `1.3.0`, and reopen
   the `main` bootstrap (below).

---

## Building `:dev` — it does not publish itself

**The publish workflow cannot run.** GitHub fires `workflow_run` only for a
workflow file on the **default branch**, and `main` has no `.github/workflows/`
directory, so `docker-publish.yml` is not registered:

```bash
$ gh workflow list --all
CI	active	341412730      # the only workflow GitHub knows about
```

`workflow_dispatch` needs the same thing, so the Actions-tab override cannot help
either. Build by hand:

```bash
# one-time, only if you want arm64
docker run --privileged --rm tonistiigi/binfmt --install arm64

docker buildx build --platform linux/amd64,linux/arm64 \
  -t bozodev/glimpse-media-viewer:dev --push .
```

Drop `,linux/arm64` for a much faster x86-only build. Run `make docker-smoke`
first.

PR #13 existed to fix this by putting the workflows on `main`; it was **closed
unmerged** because nothing should reach `main` yet. Nothing was lost — it was a
cherry-pick of commits already on `dev`. Reopening that work is step one whenever
`main` is back on the table.

**The `v1.3.0` tag is already pushed and is load-bearing.** Docker Hub carried
tags to `1.3.0` from years of manual builds while this repo had none. `VERSION`
reads `1.3.0`; without a matching tag the publish workflow would treat it as
unreleased and overwrite the published image. The first real release must bump
**past** `1.3.0`.

---

## Testing the frontend — read this before trusting a green run

Five bugs reached the user while both the suite and a headless browser check
reported everything fine.

**`chromium --headless --virtual-time-budget=… --dump-dom` cannot verify this
app.** Under `--virtual-time-budget`, `requestAnimationFrame` never fires — and
Alpine's transitions, the scroll lock and the focus manager all sequence on it.
Every overlay sits frozen at `overlay-shut overlay-opening`. Such a run verifies
that overlays render **shut**; it never opens one.

Drive a real browser over the DevTools protocol instead. `websocket-client` is
installed:

```bash
chromium --headless --disable-gpu --no-sandbox \
  --remote-debugging-port=9333 --remote-allow-origins='*' \
  --user-data-dir=/tmp/cdp-profile about:blank &
```

`--remote-allow-origins='*'` is required or the handshake 403s. Then
`Emulation.setDeviceMetricsOverride` for the viewport and `Runtime.evaluate` to
click and assert.

**Test at 1280px *and* 390px.** The overlay system behaves differently at each by
design, so one width proves nothing:

| | 1280px | 390px |
| --- | --- | --- |
| genre overlay | centred dialog | bottom tray |
| grab handle | hidden | shown |
| close button | shown | hidden |
| hamburger | hidden | shown |

The grab handle and close button rows are **inverses of each other**, and that is
the property to check rather than either row alone. Every overlay that wears both
shapes must carry both controls in its markup, because each is hidden at the
width where the other is shown. A panel with only one of them has no affordance
at some width — which is what the Actions tray did between 769px and 992px.

**A passing markup test is not a passing feature.** The suite asserted overlays
existed with correct ARIA and passed while `openModal()` threw on a renamed
selector. When renaming anything the JS queries, make sure a test resolves the
selector against classes that actually exist —
`test_openmodal_selectors_match_the_markup` does. Every regression test in
`tests/test_overlay_markup.py` was demonstrated to fail against its specific bug
before being committed; keep that habit.

---

## Open questions the user has not answered

1. **The manifest `theme_color` mapping looks transposed**: Jellyfin `#101010`,
   Emby `#0f1419`, Plex `#131313`. Blue-tinted `#0f1419` on green-branded Emby.
   Preserved exactly as the old implementation had it. Raised twice, unanswered.
2. **Should the detail overlay be a tray on desktop too?** Specified as a dialog.
3. ~~**Should the genre filter be a popover anchored to its button on desktop**
   rather than a centred dialog?~~ **Answered: no.** One overlay at both widths,
   for the genre filter and the server switcher alike. The same question was
   raised again during `restyle-tray-controls` — the desktop genre control had
   been reported as "still showing a tray" — and settled the same way. Two
   implementations of one control is what the rewrite deleted, and it is why
   every genre feature in this app previously had to be written twice.

2 is recorded under Open Questions in
`openspec/changes/convert-overlays-to-trays/design.md`.

---

## Traps worth knowing

Most are already in [CLAUDE.md](../CLAUDE.md); these are the ones that cost time.

- **`docker-compose.yml` is frozen** and `tests/test_compose_surface.py` asserts
  its environment surface exactly, in both directions. A *new* variable fails it
  as surely as a removed one.
- **The `.claude/commands/` slash commands load at session start.** They were
  added mid-session, so `/ship` and `/opsx:*` will not resolve until Claude Code
  is restarted. That is not a broken file.
- **Never strip CSS by substring match.** `.mobile-menu` matched
  `.mobile-menu-button` and silently deleted the hamburger's entire styling,
  including its `display: none`.
- **`openspec` is installed under Node 16** and prints PostHog errors on every
  invocation. Cosmetic; reinstalling under Node 18+ would silence it.
- **Node 18+ is required** for the lint toolchain (`nvm use 18.20.8`); the shell
  default here is Node 16.

---

## Punch list before `main` — stated 2026-08-25

After reviewing the restyled trays ("this looks a lot better"), the user listed
six things to get right before anything reaches `main`. Several were measured in
that session, and the findings change what the work is — read these before
assuming any item is unstarted.

### 1. The desktop genre control should not be a tray

**It already isn't.** Verified at 1280px against a container built from `dev`:
the genre overlay is a centred dialog — `align-items: center`, grab handle
hidden, close button shown. Either a stale build is being viewed (this exact
report was traced to a stale service-worker cache once already) or the ask is for
a **dropdown anchored to its button**.

Confirm which before building. An anchored dropdown reverses open question 3
above, answered "no — one overlay at both widths". That is a product decision,
not a bug fix.

### 2. Mobile trays are choppy and don't look like they rise from the bottom

The durations are **not** the difference: Glimpse 200/280/150ms against Marquee
180/300/120ms (`--dur-base` / `--dur-slow` / `--dur-exit`). The open genuinely
animates `translateY(285px) → 0`. Two leads:

- **The likely one.** `web/index.html` renders *every* item as a DOM node
  (`mediaData.forEach`, ~line 2401); only the images lazy-load. A real library is
  ~7,000 items. The scroll lock sets `position: fixed` on `<body>` on the same
  frame the tray starts moving, forcing a full relayout of every card at frame 1.
  Marquee's wall is paginated, so its document is far smaller. **A few-hundred
  item fixture will never reproduce this — seed thousands.**
- Alpine strips `overlay-opening` at ~275ms while the panel is still ~8px from
  rest, handing the remainder to `.sheet__panel`'s base 200ms transition — an
  easing discontinuity at the end of every open. On close the panel reaches 236px
  down while the root is still at 0.61 opacity, so the panel outruns its backdrop.

### 3. Every tray needs the same handle-to-title gap

A measured defect — three different distances to the glyph. The eye measures to
the glyph, so half-leading counts:

| Overlay | head padding-top | line-height | gap to glyph |
| --- | --- | --- | --- |
| Genre / Server / Actions | 14px | 26.4px | 18.4px |
| Detail | 16px | **19.36px** (override) | 16.9px |
| Roulette | 16px | 26.4px | 20.4px |

`.sheet__head` pads 14px and `.modal__head` 16px, and `.modal-title` carries a
`line-height` override — precisely the edit `overlays.css` warns "is the edit
most likely to undo this quietly".

### 4. Verify the PWA caches properly — **DONE, pending `:dev`**

Asset freshness was fixed earlier (see the caching table in
[CLAUDE.md](../CLAUDE.md)). `cache-for-speed-not-for-offline` finished the job.
Measured against a 400-item library by reading the container's own nginx access
log — **a repeat visit requests zero posters** and paints its grid from cache,
while the library data is fetched every time.

**This change reversed direction mid-flight, and the reversal is the point.** It
started as `serve-the-library-offline` and made the app fully offline-capable —
snapshots cached, configuration retained, a "showing saved library" badge. That
was built and verified 30/30, then withdrawn: the user does not want a possibly
stale library displayed when the container is stopped, and the punch-list item
was always a question about *speed*. What survived is the part that was always
worth doing — deleting a cache fallback that had never once returned anything,
and stopping any error response being answered from cache.

**Two findings from the withdrawn work are load-bearing. Do not re-derive them:**

- A browser dispatches **no fetch event for a synchronous XHR**, and the boot
  read of `config.json` is one. The service worker never sees that request and
  cannot cache or answer it. "Just cache config.json too" is not a one-line
  change; it is impossible from the worker.
- The container's nginx declares `error_page 500 502 503 504 /50x.html` but ships
  no `50x.html`, so every 5xx it generates is rewritten to a 404. Out of scope,
  worth knowing.

Also worth knowing: behind a **reverse proxy**, a stopped container makes the
proxy return 502/504 rather than the connection being refused — the network
failing, reported as a status. Harmless now, since the data routes never consult
a cache. It would matter to anyone who reintroduces offline support.

### 5. Animate the movies/TV swipe

Not started. The outgoing grid sliding out as the new one arrives. Both grids
already exist as `#movies-content` and `#tvshows-content`, so a transform-based
slide is plausible — but see the DOM size note in item 2 before animating a
container holding thousands of nodes.

### 6. Confirm CI/CD builds `:dev` and `:latest`

The workflows are sound; the problem is where they live. **`main` has no
`.github/workflows/` directory at all** — confirmed by
`git ls-tree main .github/workflows/` returning nothing.
`docker-publish.yml` triggers on `workflow_run`, which GitHub registers only from
the default branch, so it has never fired and no image has ever been published by
CI. Docker Hub secrets are set; CI itself runs green on every `dev` push.

Expect a chicken-and-egg on the first merge: landing the file on `main` is what
registers the trigger, so that first merge may itself publish nothing. Verify
`:latest` on Docker Hub afterwards and be ready to publish it by hand once.
