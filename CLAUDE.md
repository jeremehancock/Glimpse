# Glimpse

Self-hosted, read-only web viewer for a Plex / Jellyfin / Emby library. Python
fetchers snapshot metadata and artwork to a mounted volume on a cron schedule;
nginx serves a static single-page interface that browses that snapshot. Ships as
a single Docker image.

Detail lives elsewhere — this file is only what's expensive to get wrong:

| For… | Read |
| --- | --- |
| Branch/release flow, OpenSpec commands, toolchain | [docs/development-workflow.md](docs/development-workflow.md) |
| The Docker image, the entrypoint, the local smoke test | [docs/docker.md](docs/docker.md) |
| Project context + the capability map | `openspec/config.yaml` |
| The release state machine and its guardrails | `.claude/commands/ship.md` |

## `docker-compose.yml` is frozen

**This is the one rule that outranks everything else here.** Every user has a
copy of that file. Changing it does not fail the build, does not fail a lint, and
does not show up in the smoke test — it breaks installs one `docker compose up`
at a time, after the release has shipped.

Frozen means all of it: the image name `bozodev/glimpse-media-viewer`, the
service name, `9090:80`, `./data:/app/data`, the commented-out
`./logo.png:/app/web/images/logo.png` override, and every environment variable it
names, with the semantics it names them with.

`tests/test_compose_surface.py` asserts the variable list **exactly**, in both
directions. A new variable fails it just as a removed one does, and that is
deliberate: a variable the app reads but a user's file does not set means the
fallback is now a decision someone has to make on purpose. When that test fails,
do not edit the test. Go decide whether the change is worth what it costs, and if
it is, move the fixture in the same commit and say in the PR what an existing
user has to do. The answer should almost always be "nothing".

The app is read-only and unauthenticated by design: there is no path that writes
to a media server, and no login. Anyone who can reach the port sees the library.
Adding either is a spec change, not a wiring decision.

## Workflow: spec-driven, not test-driven

Every capability is defined by an OpenSpec spec **before** it is built. Don't
start writing code from a bare description.

```
/opsx:explore → /opsx:propose → (you review) → /opsx:apply → /ship → /opsx:archive
```

- A change MUST target an existing capability from the map in
  `openspec/config.yaml` — never invent a capability named after the change.
- Run `openspec validate <change> --strict` before coding. The usual failure is
  a scenario not using exactly four `#` (`#### Scenario:`).
- Tests are written alongside the implementation and verified at the end of a
  change, not first. Implementation tasks precede their test tasks.

## `/ship` owns everything after `/opsx:apply`

Commit, push, VERSION bump, archive, PR, resync. **Use it — don't hand-roll
those steps.** It detects the current state and does the next right thing, so
it's safe to run at any point and again later. Running the steps manually
bypasses its guardrails, which is the main way this project gets broken.

`/ship` does not write code — if tasks are incomplete it stops and sends you
back to `/opsx:apply`. It never merges a PR, and never bumps `VERSION` without
asking. `ship.md` is the authority on all of that; don't second-guess it from
here.

Two rules that hold **even when you aren't running `/ship`**:

- **Never archive before the user has validated the `:dev` image.** Archiving
  rewrites `openspec/specs/`, the source of truth.
- **Code and specs ship together** — the archive commit belongs in the same PR,
  or `main` gets the code while its specs describe the old behavior.

## Gates — both run before any commit

**Toolchain.** Both must pass; never commit around a failure.

```bash
make lint     # ruff check + ruff format --check + eslint + prettier --check
make test     # pytest
make fmt      # apply every fix lint would ask for
```

CI runs exactly these on every push, plus a Docker build and a container smoke
test. A red CI publishes nothing.

`make lint` needs `ruff` on PATH and Node 18+ with `npm ci` already run. Neither
is in the runtime image — they are development tooling only, and **nothing in
`web/` is built or bundled.** nginx serves those files exactly as authored, so
never introduce a step that compiles, minifies, or transpiles them.

**The gate does not cover the image.** CI builds it only *after* you push, so a
`Dockerfile`, `config/` or entrypoint change needs `make docker-smoke` locally
first. See [docs/docker.md](docs/docker.md).

**Docs.** Check whether the change makes `README.md`, `docs/`, or this file
stale, and fix it in the **same** commit. Docs drift silently — nothing fails
when they fall out of sync, so checking every time is the only defense. If
nothing user-facing changed, say so explicitly rather than inventing edits.

## Branches

Work on **`dev`**. Never commit directly to `main` — it's release-only, and PRs
are merged on GitHub, so the local `main` ref is usually stale (use
`git fetch origin main:main` before comparing).

`VERSION` is load-bearing: it drives the pinned image tag, the git tag, and the
GitHub Release. Don't edit it outside `/ship`.

**`VERSION` starts ahead of git.** Docker Hub carries tags up to `1.3.0` from
years of manual builds; this repo has no git tags at all, because the release
workflow is new. So `VERSION` reads `1.3.0` to describe what is published, and
the first release cut through CI must be a **bump past it**. Merging to `main`
with `VERSION` still at `1.3.0` would tag `v1.3.0` and overwrite the published
`1.3.0` image with different code. `/ship` checks for this; don't route around
it.

## Code conventions

- **The entrypoint generates files. It never mutates authored ones.** Exactly two
  files are generated: `/app/web/config.json` and `/app/web/manifest.json`.
  `index.html`, `sw.js`, `offline.html` and everything under `images/` are
  authored and read-only at runtime.

  The distinction is not stylistic. A whole-file write is deterministic and its
  output does not depend on how many times the container has started. The old
  entrypoint rewrote `index.html` with `sed` on every boot — per-server themes,
  an injected server dropdown, four copies of the page — and shipped
  `cleanup_duplicate_server_content()` and `fix_corrupted_files()` to repair the
  damage it did to its own output. `sed` fails *silently* when a pattern does not
  match and is not idempotent over its own output; that pairing produced most of
  this project's historical bugs. It is not coming back.

  Per-server theming is `data-server="jellyfin"` on `<html>` plus CSS custom
  properties. If a behavior seems to need the entrypoint to edit a file under
  `/app/web`, it is a spec change to `application-shell`, not a wiring decision.
  `make docker-smoke` asserts the web root is clean after boot.
- **The frontend reads `config.json` once at boot into a single store.** Never
  re-read it, and never add a second source for a setting. The environment is
  read by the entrypoint and by nothing else.
- **A missing or malformed `config.json` is reported, never defaulted around.** A
  silent fallback recreates the exact failure this project spent years on: a
  misconfigured install that looks like a working one, quietly showing the wrong
  library — or an empty one indistinguishable from a server with no media.
  - **There is no exception, and one was tried.** `serve-the-library-offline`
    briefly retained the last configuration so an installed app could open away
    from its network. It was reverted: the app cannot tell the user whether what
    they are looking at is current, and showing a library that might be out of
    date is the same ambiguity this rule exists to refuse. If it comes back it
    is a product decision, not a wiring one.
- **`Dockerfile` copies `scripts/` as a directory, not file by file.** The
  per-file list silently omitted `glimpse_config.py` when it was added, and the
  container refused to start at runtime rather than failing the build. A
  directory copy cannot drift from what the entrypoint invokes.
- **Emby and Jellyfin are one adapter with two identities**, not two code paths —
  their APIs are compatible, which is why one fetcher already serves both. A fix
  applied to one that isn't applied to the other is a bug, and the reason
  library-exclusion had to be fixed twice.
- Artwork is re-downloaded only when its MD5 changes. The checksum store is
  per-server and lives on the mounted volume, so a first run after an upgrade
  must not invalidate it — that would re-download an entire library.
- **There is one overlay system and every overlay uses it.** `.sheet` docks to
  the bottom edge, `.modal` centres, and `.modal--tray-on-touch` is a dialog that
  becomes a tray on a phone. Alpine owns *when* an overlay shows (`x-show`,
  `x-transition`); `web/assets/overlays.css` owns how it looks;
  `web/assets/overlays.js` owns the drag gesture, the scroll lock and focus.
  Never hand-roll a seventh — six bespoke overlays is what this replaced.
  - **The gesture, the scroll lock and the focus manager all find their subjects
    in the DOM, never from a registry.** Deliberate: a registry has to be updated
    when an overlay is added, and forgetting is silent — the overlay opens, looks
    perfect, and simply cannot be swiped, does not lock the page, and strands a
    keyboard user. Keying on the DOM makes correct markup the only requirement.
- **An overlay panel declares `role="dialog"`, `aria-modal="true"` and
  `tabindex="-1"`, and nothing else makes it focus-managed.** One added without
  them opens and leaves a keyboard user on the page behind the backdrop with no
  way in. `tests/test_overlay_markup.py` asserts every panel in the markup
  carries all three; it cannot catch one created at runtime.
  - **A control that closes its own tray and opens another must move focus to
    something still on screen before the first one hides.** Alpine hides on the
    flush *after* the handler, and hiding a focused element hands its focus to
    `<body>` — which the focus manager reads a frame later to decide where to
    return focus to, and an origin rooted at the body is the one case it declines
    to restore. The overlay opens correctly and dismissing it drops the keyboard
    user at the top of the page. Nothing errors, and the pointer path looks
    perfect. Call the opening control's `.focus()` first. Both places that do
    this today — the Actions tray's genre button, the detail overlay's trailer
    button — say so in a comment.
  - **The drag region and the scrolling region must stay separate elements.**
    `.sheet__grip`, `.sheet__head` and `.modal__fixed` carry `touch-action:
    none`, which the browser honours only if they are not themselves the
    scroller. Nesting a head inside `.sheet__body` hands the gesture back to the
    browser as a scroll — silently, with no error and no visual difference on a
    desktop.
  - **A panel may have a third region: `.modal__fixed`, which holds still while
    `.modal__body` scrolls under it.** The detail overlay pins the item's poster
    and metadata there so they stay in view. It is a real element, never
    `position: sticky` on a child of the body — a sticky element is still inside
    the scroller, so its `touch-action: none` cannot be honoured. **Never give it
    an `overflow`.** Bounding it by capping what grows inside it (the title is
    line-clamped) keeps the drag gesture working; giving it a scrollbar is the
    same silent failure as nesting a head in a body, reached from the other side.
    The item's artwork fills it with `inset: 0`, so the artwork's extent is a
    consequence of the layout rather than a height someone has to re-guess per
    viewport — it used to be a hardcoded `280px` that overshot into scrolling
    content on every phone.
  - **A rule that hides a page control must name where that control lives.**
    `.sort-toggle { display: none }` in a mobile media query meant "the header's
    sort controls", but the Actions overlay's body *is* a `.sort-toggle`, so the
    rule emptied it — handle, title, and nothing else. Scope such rules to
    `.header-content`. The pair that hides a page control and shows the overlay
    trigger that replaces it belongs in **one media query**: split apart they had
    drifted to 992px and 768px, leaving every width between with neither.
  - **An overlay that wears both shapes needs BOTH affordances, not either.**
    A grab handle *and* a close button. They are not alternatives — each is
    hidden at the width where the other is shown: the grip goes above 768px
    because a mouse has no drag to make, the × goes below it because the handle
    is the thumb-reachable target and two ways to close is worse than one. So a
    panel carrying only a grip has nothing at pointer widths. The Actions tray
    did exactly that, and between 769px and 992px — where the hamburger still
    opens it — it appeared as a dialog with neither. Backdrop and Escape worked;
    nothing on screen said so. A plain `.modal` is the exception: centred at
    every width, never shows a grip, so its × is the whole affordance.
  - **A closing overlay is not an open one.** Both the scroll lock and the focus
    manager skip anything carrying `.overlay-closing`. Waiting for `display:none`
    instead pins the page for a beat after every dismissal, so the first flick is
    swallowed, and holds focus inside an overlay the user already closed.
  - **`.genre-item` is the shared tray-choice control.** Both the genre tray and
    the server switcher build their entries with it, deliberately — they are one
    control offering different things, which is why the genre filter no longer
    has to be written twice. A change to it lands in both, and that is the point;
    styling them apart is how they drift. It carries a `__label` and an optional
    `__count`, and it must declare its own background, border, radius, display
    and font: it is a `<button>`, so anything it does not state, the browser
    states for it. That is the whole of how it came to render as white system
    boxes reading `Action794`.
  - **An overlay's panel is not a bare wrapper — it has three regions.** A grip,
    a head and a body, even where the content is a single spinner. The roulette
    had none of them, so `.modal--tray-on-touch` alone would have produced a tray
    with nothing to drag, no × (the modifier hides it on touch), and a backdrop
    that deliberately does not dismiss: an overlay with no way out. The modifier
    and the regions arrive together or not at all.
  - **The Actions tray is teleported to `<body>` on purpose.** `backdrop-filter`
    makes an element a containing block for its fixed-position descendants, so
    the moment the header becomes translucent a tray nested inside it renders
    squashed into the height of that bar. It looks correct on a desktop viewport
    either way, which is what makes it easy to "simplify" back into a bug.
    - **A control inside that tray must be bound after `alpine:initialized`.**
      Until Alpine boots, the tray is inert `<template>` content that
      `querySelectorAll` cannot reach — and Alpine is a `defer` script, so it
      runs *after* the page's inline `<script>` has finished. Every binding pass
      that ran at parse time found only the header's copies, and left the tray's
      sort buttons, server switcher and install button with no handlers at all.
      Nothing throws: the control highlights, the tray dismisses, and nothing
      happens, so it reports as the feature being missing rather than as a bug.
      `bindRelocatedControls()` is the hook; the passes are idempotent and the
      parse-time calls stay, so the header still works if Alpine ever fails.
      Note that only *binding* was broken — queries made at click time reach the
      teleported markup fine, which is why the tray's copy correctly showed the
      active sort while doing nothing. That divergence is what made it look
      wired.
    - **An action inside an overlay cannot scroll the page.** The scroll lock
      pins the body, so `window.scrollTo` moves nothing, and the lock then
      restores the position captured when the overlay opened — overwriting it a
      frame later. Call `window.GlimpseOverlays.scrollPageTo(y)`, which sets
      the restore target while locked and scrolls normally when not, so one
      handler serves a control that exists both in the page and in a tray.
- **Page chrome ranks BELOW every overlay.** The ladder is `--z-chrome` (30) <
  `--z-sheet` (50) < `--z-modal` (55), declared in `web/assets/tokens.css` and
  read from there — a chrome element never restates a number. `.header` was 100
  and `.scroll-to-top` was 1000, so a dialog rendered *under* the header on a
  desktop and every tray on a phone slid in behind a header that stayed lit and
  unblurred above its own backdrop. An overlay's backdrop exists to withdraw the
  page; chrome that outranks it is not withdrawn.
- **Alpine is vendored at `web/assets/alpine.min.js`, never loaded from a CDN.**
  A CDN script is a network dependency that fails exactly when the network is
  what failed — the one moment an offline-capable PWA has to work. Cached by the
  service worker for the same reason, and excluded from ESLint and Prettier
  because it is third-party.
- **`/assets/` is network-first, at all three caching layers. Never "optimise"
  any of them back.** Nothing under `web/` is built or bundled, so these
  filenames carry no content hash and never will: a changed file keeps its URL.
  Anything that holds them therefore pins a client to the build it first loaded.

  | Layer | Setting | Where |
  | --- | --- | --- |
  | Service worker | `networkFirstWithCacheFallback`, not cache-first | `web/sw.js` |
  | Browser HTTP cache | `no-cache` on `/assets/` **and `/sw.js`** | `config/nginx.conf` |
  | The worker's own fetch | `cache: 'reload'`, including the install precache | `web/sw.js` |

  All three had to change together, and each one alone looks harmless. The
  worker's `fetch()` consults the HTTP cache, so a long `max-age` in nginx
  defeats a correct strategy. `/sw.js` was matched by the `.js` extension rule
  and cached for a week — the code that decides the caching policy, frozen,
  withholding the upgrade that would fix it. And correcting a header cannot
  retract an entry the browser was already told to keep, which is what
  `cache: 'reload'` is for: it heals an already-poisoned client on its next load
  instead of in seven days.

  This cost a full diagnostic session. It presented as a fixed bug still being
  broken, which is indistinguishable from a regression until you compare the
  served bytes against the repo. `/images/` and `/data/` keep their 7-day cache;
  they are genuinely static.
- **The service worker is here for SPEED, not for offline browsing.** Artwork is
  stale-while-revalidate and the app's own assets are network-first with a cache
  fallback, so a repeat visit paints without waiting on round trips. **The
  library data — `config.json` and `/data/*.json` — is never cached, in either
  direction.**
  - **Never add a cache fallback to the data routes.** A stale grid is
    indistinguishable from a current one and an empty grid is indistinguishable
    from a library with no items; the app cannot tell the user which they are
    looking at, so it does not show them something that might be wrong. If that
    is ever revisited, it is a product decision, not a wiring one.
  - **Never write the data to a cache "for later" either.** That is how the
    original defect read: `/config.json` and the snapshots were fetched with a
    `caches.match()` fallback against a cache nothing ever populated. The line
    read correctly and had never once returned anything — live code that cannot
    succeed, which is worse than no code because it looks like a working feature
    to everyone who reads it.
  - **`config.json` cannot be cached by the worker even if you want it to.** The
    boot read is a synchronous XHR, and a browser dispatches no fetch event for
    one, so the worker never sees that request. Measured, not assumed. Without
    knowing this, "just cache config.json too" looks like a one-line change.
- **A response the server actually returned is never replaced by a cached one.**
  Only a fetch that THREW may be answered from cache. A status is the server
  speaking; the absence of a status is the network. A container whose entrypoint
  failed *answers* — serving the last response that worked over its 500 hides a
  broken install behind a working-looking one, which is this project's oldest
  failure mode reached from a new direction. `tests/test_cache_policy.py` pins
  it by shape: no strategy may read a cache inside its `try`. Cache reads belong
  before the fetch or in the `catch`, and nowhere else.
- **The offline page exists once, in `web/offline.html`.** `sw.js` used to carry
  a second copy inlined as a template literal, with the Plex palette hardcoded;
  it had already gone stale against the themed original. Cache the file, never
  inline it. It is reached only when the worker is installed, the network is
  gone, and the requested page is not cached — rare enough that nothing
  exercises it by accident, which is exactly how the inlined copy rotted.
- **A control is switched off with `aria-disabled`, never the `disabled`
  attribute, and every such binding needs a guard at the action.** The attribute
  drops a control out of the tab order, so a keyboard user is not told it is
  unavailable — they are not told it exists. `aria-disabled` announces and does
  not enforce: the click still fires, so the handler must refuse.
  - **A switched-off control never carries its reason in a tooltip.** Tooltips
    are hover-and-fine-pointer only, so a reason attached to one is a reason no
    touch user ever receives. A control with nothing to offer is usually an
    *empty* destination rather than a dead one — prefer opening it and saying so.
- Python: `pathlib` over `os.path`, type hints on anything crossing a module
  boundary, and `print()` is the fetchers' interface — `docker logs` is how a
  user watches an import run. Don't replace it with a logger that hides output.

## Docker

The image is Debian slim + Python 3.13 + nginx + supervisord + cron. The Python
version comes from the base image tag; editing the `python3-*` package names
alone doesn't change it.

Any `Dockerfile`, `config/nginx.conf`, `config/supervisord.conf` or
`config/entrypoint.sh` change needs `make docker-smoke` before pushing, because
CI only exercises the image *after* you push. Read
[docs/docker.md](docs/docker.md) first.
