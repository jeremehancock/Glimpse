# Handover — the rewrite, as of 2026-08-24

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

`make check` is green (98 tests). CI is green on `dev`.

### Two OpenSpec changes are implemented but NOT archived

```bash
openspec list
```

- **`replace-boot-time-html-rewriting`** — 50/51. Only "validate `:dev`" remains.
- **`convert-overlays-to-trays`** — 42/44. Reduced motion and real touch/swipe
  feel still need a physical device.

**Do not archive either until the user has validated a `:dev` image.** Archiving
rewrites `openspec/specs/`, which becomes the source of truth.

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

1. **Validate `:dev`** — the gate on everything else. See "Building `:dev`".
2. **Split `web/index.html` into ES modules.** The planned third change, not yet
   proposed. `index.html` is still ~4,000 lines and carries a temporary config
   adapter, marked in-file with the change name that should remove it.
3. **Then** archive both changes, bump `VERSION` past `1.3.0`, and reopen the
   `main` bootstrap (below).

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
| hamburger | hidden | shown |

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
3. **Should the genre filter be a popover anchored to its button on desktop**
   rather than a centred dialog? Specified as a dialog — one fewer presentation
   to maintain.

2 and 3 are recorded under Open Questions in
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
