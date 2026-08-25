# Handover — the rewrite, as of 2026-08-25

Glimpse is mid-rewrite, modelled on [Marquee](https://github.com/jeremehancock/Marquee).
All work is on **`dev`**. **Nothing goes to `main` until the rewrite is
finished.**

This file is a snapshot, not a specification. The specs are in `openspec/`; this
is here so the next session does not have to reconstruct the situation from git
log. **Delete it when the rewrite lands** — it is item 1 on
[pre-release-cleanup.md](pre-release-cleanup.md), which lists everything else
committed as scaffolding that must not reach a release.

---

## Where things stand

`dev` is eight commits ahead of `main`:

| Commit | What |
| --- | --- |
| `24c50e0` | Spec-driven workflow, quality gates, CI + publish pipeline |
| `8274bda` | **`replace-boot-time-html-rewriting`** — entrypoint 1,915 → 127 lines |
| `2633530` | README title fix |
| `2aa387d` | **`convert-overlays-to-trays`** — six overlays onto one system |
| `c2c2b2e` | Five regressions from the tray conversion |
| `b31068c` | **`pin-detail-header-and-fix-actions-tray`** |
| `e1d130b` | **`fix-overlay-layering-…`** + **`restyle-tray-controls`** |
| `b27d7c2` | `serve-the-library-offline` — **superseded by the next commit** |
| `fcdcb58` | **`cache-for-speed-not-for-offline`** — withdrew the offline capability |

`make check` is green (152 tests). CI is green on `dev`. `:dev` on Docker Hub was
built by hand from `fcdcb58`, **amd64 only**.

> **Every change in flight is code-complete.** The only unchecked task in each is
> ":dev validation". Nothing has been archived, because archiving rewrites
> `openspec/specs/` — still empty, since nothing here has ever been archived.
>
> **`:dev` validation is PARTIAL.** As of 2026-08-25 the user has confirmed the
> desktop genre control (punch-list item 1) and driven the caching work to a
> conclusion. They have **not** signed off the tray conversion, the layering
> fixes, or the detail overlay. Do not read "code-complete" as "validated", and
> do not archive on the strength of item 1.
>
> **Next up, in this order, set by the user:** punch-list **item 3** (tray
> handle-to-title gap), then **item 2** (choppy trays). Both have measurements
> waiting in the punch list at the end of this file — read them first.
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

1. **Punch-list item 3, then item 2** — the order the user set on 2026-08-25.
   See the punch list at the end of this file; both have measurements already.
2. **Hear out the user's remaining issues** with
   `pin-detail-header-and-fix-actions-tray` — see above. They exist and have not
   been described. This may overlap with item 3.
3. **Finish validating `:dev`** — the gate on archiving. Partially done: the
   user has confirmed the desktop genre control and driven the caching change.
   See "Building `:dev`".
4. **Split `web/index.html` into ES modules.** The planned change, not yet
   proposed. `index.html` is still ~4,000 lines and carries a temporary config
   adapter, marked in-file with the change name that should remove it.
5. **Regenerate the screenshots in `assets/`.** All six predate the rewrite —
   `screenshot-details-*` in particular show the detail view as a centred box
   with a corner close button, which is the presentation the tray conversion
   replaced. They are served from `main`, so they will not look wrong to anyone
   until the rewrite merges, and then all six will at once. This needs a real
   media library, so it is a release-time task rather than a per-change one.
6. **Then** archive all six changes, bump `VERSION` past `1.3.0`, and reopen
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

Drive a real browser over the DevTools protocol instead. **The driver is
committed — do not rebuild it.** See [`tools/`](../tools/README.md):

```python
from tools.browser import Browser, nginx_requests
```

`Browser.measure(selector)` returns rendered geometry plus type metrics, which is
what punch-list item 3 needs. `tools/seed_library.py` generates a library at any
size, which is what item 2 needs — it defaults to 7000 items for that reason.

**Do not measure caching with `PerformanceResourceTiming.transferSize`.** It
reads `0` for anything a service worker handled, whether the worker went to the
network or not — so "served from cache" and "fetched through the worker" look
identical. That reported the library snapshots as cache hits when they were not.
Read the container's own access log instead:

```bash
docker exec <container> tail -n +<N> /var/log/nginx/access.log
```

It is the only witness that cannot be fooled by the timing API.

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
six things to get right before anything reaches `main`. Several have since been
measured or closed — read each entry before assuming it is unstarted.

**Work order for the next session, set by the user on 2026-08-25:**

| Order | Item | State |
| --- | --- | --- |
| **1st** | 3 — tray handle-to-title gap | measured, not fixed |
| **2nd** | 2 — choppy trays | two leads, not reproduced |
| then | 5 — movies/TV swipe animation | not started |
| — | 1 — desktop genre control | **CLOSED, confirmed by the user** |
| — | 4 — PWA caching | **DONE**, pending `:dev` sign-off |
| — | 6 — CI/CD publishes | **answered**; needs the `main` bootstrap |

### 1. The desktop genre control should not be a tray — **CLOSED**

**Confirmed fixed by the user on 2026-08-25**, against the `:dev` image built
from `fcdcb58`. It presents as a centred dialog at pointer widths: `.sheet` gets
`align-items: center` above 768px, the grip is hidden and the × is shown.

Worth knowing why this took two rounds: the behavior was already correct in the
source, and the earlier report was a **stale service-worker cache** serving old
CSS against new markup — the same failure recorded in "Traps worth knowing". If
a fix ever appears not to have landed, compare the served bytes against the repo
*before* touching the code.

The anchored-dropdown option was never needed. Open question 3 stands answered:
one overlay at both widths.

### 2. Mobile trays are choppy and don't look like they rise from the bottom

**Not addressed. No code has changed, and it has not been reproduced.**

The durations are **not** the difference: Glimpse 200/280/150ms against Marquee
180/300/120ms (`--dur-base` / `--dur-slow` / `--dur-exit`). The open genuinely
animates `translateY(285px) → 0`. Two leads:

- **The likely one.** `web/index.html` renders *every* item as a DOM node
  (`mediaData.forEach`, ~line 2551); only the images lazy-load via
  IntersectionObserver. The user's library is ~7,086 items. The scroll lock sets
  `position: fixed` on `<body>` on the same frame the tray starts moving, forcing
  a full relayout of every card at frame 1. Marquee's wall is paginated, so its
  document is a fraction of the size.

  **A few-hundred-item fixture will never reproduce this.** The
  `cache-for-speed-not-for-offline` session drove a real browser against a
  **400-item** library and saw nothing wrong — that is not evidence of health.
  **Seed thousands** before concluding anything.

- Alpine strips `overlay-opening` at ~275ms while the panel is still ~8px from
  rest, handing the remainder to `.sheet__panel`'s base 200ms transition — an
  easing discontinuity at the end of every open. On close the panel reaches 236px
  down while the root is still at 0.61 opacity, so the panel outruns its own
  backdrop.

Measure before changing anything, and measure on a real browser — see "Testing
the frontend" above.

### 3. Every tray needs the same handle-to-title gap

**Measured, not fixed. Start here.** Confirmed against `fcdcb58`.

Half of the original defect is already gone: the `line-height` override on the
overlay head's title was removed by `restyle-tray-controls`, and
`web/assets/overlays.css` now carries a comment explaining why line-height must
stay inherited. **Do not reintroduce one** — it changes nothing about the padding
anyone would think to check.

What remains is plain padding, and it disagrees at **both** widths, in opposite
directions:

| | `<768px` (tray) | `≥768px` (dialog) |
| --- | --- | --- |
| `.sheet__head` — genre, server, Actions | **14px** | **18px** |
| `.modal__head` — roulette | **16px** | **16px** |

Both sit under the same `.sheet__grip` (`padding: 12px 0 0`) and both title
elements are `1.1rem` with inherited line-height, so the padding is the whole of
the difference. The desktop override lives in the `min-width: 768px` block and
exists because the grip is hidden there — the title needs the dialog's own top
padding instead. Whatever it becomes, it has to stay deliberate for that reason.

**The detail overlay is a different problem and should be judged separately.** It
has no `__head` at all: `.modal__fixed` holds the grip, the artwork, the poster
and `.modal-title` (the *item's* title, `2.2em` / `line-height: 1.1`, line-clamped
to 3), with `.modal-header` padding `30px`. So "the gap below the handle" there is
grip → item title across a different box. Making it numerically match the other
five may not be what looks right; decide with your eyes on a phone, not with a
calculator.

The eye measures to the **glyph**, so half-leading counts. Measure rendered
positions in a real browser rather than adding up the CSS.

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
container holding thousands of nodes. **Item 2 and item 5 are probably the same
underlying problem**: if a full relayout of ~7,000 cards is what makes a tray
choppy, it will make a grid slide choppy too. Doing item 2 first may resolve
this one, or at least tell you what it costs.

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
