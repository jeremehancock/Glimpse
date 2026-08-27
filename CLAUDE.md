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

**Nor does it cover the workflows themselves.** They only ever run on GitHub, so
a mistake in `.github/workflows/` surfaces after a push and — for the publish
workflow — sometimes not even then. `tests/test_workflow_actions.py` pins every
action's version exactly, in both directions, the same way
`test_compose_surface.py` pins the compose surface, and for the same reason: a
workflow file is edited rarely and read less often, so a version drifts by
*nothing happening to it*. **An intentional bump is supposed to fail that test.**
Move the table in the same commit; never relax the assertion to get past it.

What it cannot do is tell you a pinned version has gone stale — that needs the
network, and a gate that needs the network fails on GitHub's bad days rather than
on this repo's. Runtime deprecations arrive in a build log, and they undercount:
the warning enumerates the actions that *ran*, so one behind an `if:` is silently
omitted. `softprops/action-gh-release` was missed exactly that way. When a
deprecation is reported, check every action's `action.yml`, not the warning text.

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

**`VERSION` must always bump past what Docker Hub already carries.** It describes
what is published, not what the git history contains — Docker Hub held tags up to
`1.3.0` from years of manual builds before this repo had any tags at all.
`v1.3.0` and `v1.4.0` are now pushed and load-bearing: the publish workflow reads
`VERSION`, and a version with no matching tag is treated as unreleased. Merging
with `VERSION` unchanged republishes that tag over the existing image with
different code. `/ship` checks for this; don't route around it, and don't delete
those tags.

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
- **A refresh NEVER deletes what it is replacing.** `movies.json` and
  `tvshows.json` are written to temp files beside them and renamed into place
  once **both** are complete — `scripts/snapshot_io.py`, and nothing may write a
  snapshot any other way. nginx serves that directory to a page that can load at
  any instant, so a writer has to be correct at every moment of a run, not only
  at the end of one.
  - **The old code deleted both files as its FIRST act.** So every scheduled
    import put the site into `Failed to load movie data` for its whole duration
    — not down, *broken*, which is harder to recognise and much harder to
    diagnose. Measured against a 25-item mock: **1,902 of 2,092 reads during a
    run got a missing file**, plus one caught mid-truncation. After: 0 of 1,959.
  - **That is also why a failed fetch used to destroy the library.** Both
    fetchers give up early on several conditions and every one of those paths
    ran *after* the delete, so a media server restarting when cron fired left an
    empty library until a later run succeeded — indistinguishable from a server
    with no media, the ambiguity this project refuses everywhere else. The
    safety now comes from never having deleted anything, not from a restore
    path: a restore only runs if the process survives to run it, and an OOM or a
    killed container does not.
  - **Set the mode on the TEMP file.** A rename carries the mode and owner the
    temp had, so a mode fixed afterwards is fixed too late: the swap is flawless
    and nginx answers **403**. `make test` has no web server, so
    `tests/test_snapshot_publishing.py` forces a hostile umask to check it —
    without that the assertion passes on a publisher that never sets the mode at
    all, because the usual 022 umask produces 0644 by coincidence. It did.
  - **Register a temp for cleanup BEFORE writing it, not after.** Registering on
    the way out cleans up every temp except the one that failed — the only one
    that is half-written.
- **A restart re-imports a server only when its settings changed.** Each server
  records a hash of its URL, token and exclusion list at
  `data/<server>/fingerprint`, written **only after an import succeeds**. The
  entrypoint `cmp`s it and skips the fetch on a match; a missing file and a
  differing one take the same branch, so "never imported" needs no second
  condition. `exec supervisord` stays on the last line — once a restart skips
  its fetches there is nothing slow ahead of it.
  - **Only those three settings, and the set is pinned in both directions.**
    They are the only ones that change what a snapshot *contains*.
    Re-importing a large library because someone changed `APP_TITLE` would be a
    regression. `tests/test_fetch_fingerprint.py` fails when `Server` gains a
    field, the same way `test_compose_surface.py` fails on a new variable and
    for the same reason.
  - **A hash, never the values, and `json.dumps` never a join.** `/app/data` is
    served by nginx on an app with no login, so the token cannot go there. And a
    URL and a library name both admit commas, so joined text collides — a
    collision means a fingerprint that *matches when the settings differ*, which
    silently withholds the user's change. Same call, same reason, as
    `renderSignature()`.
  - **Writing it before the fetch succeeds is the whole defect it prevents.** It
    would assert the data came from the current settings; a subsequent failure
    makes that false, and the next restart believes it, skips, and withholds the
    change with nothing on screen or in the log to say so.
  - **The fetchers had to start exiting non-zero first.** `main()` ignored what
    `fetch_and_save_data()` returned, so the process exited 0 whether the fetch
    worked or not — and the entrypoint's "initial fetch failed" warning had
    never once run. Without that, every fingerprint would be recorded after a
    failure too.
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
  - **The two heads are ONE rule, and no overlay title sets `line-height`.**
    Every overlay wearing the grab handle holds its title the same distance
    below it, and that distance is measured to the **glyph**, not to the top of
    the line box — so a title's half-leading is half the number. `.sheet__head`
    and `.modal__head` therefore share their vertical padding in a single
    selector list and differ only in horizontal inset. Two rules is the defect:
    they were 14px and 16px, and nothing said they were related.
    - The other half is why it took a browser to find. `.modal-title` set
      `line-height: 1.1` against the inherited `1.5`, inside a rule whose four
      other declarations were all outranked by `.modal__head h2` and did
      nothing. So the padding — the thing anyone checks — looked fine, the rule
      looked authoritative, and the overlays sat at three different gaps
      (18.4px, 16.88px, 20.4px) that partly cancelled on one and compounded on
      another. **A rule that appears to set an element's type must set it**;
      dead declarations are where the next live one hides.
    - The pointer-width bump that replaces the hidden handle is keyed
      `.sheet__grip ~ …head`, naming both heads. `~` and not `+`, because
      `.modal-backdrop-art` sits between the detail overlay's grip and its head.
      It stays inside the media query that hides the grip: a sibling selector
      matches a `display: none` grip, so the selector alone means "has a grip in
      the markup" and the breakpoint supplies the rest. Same pairing rule as the
      affordances — split them and a width exists with the wrong spacing.
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
    nothing on screen said so. **There is no longer a plain `.modal`** — every
    overlay wears both shapes, so every one needs both. A plain `.modal` used to
    be the exception (centred at every width, never shows a grip, so its × was
    the whole affordance), and the trailer was the last one.
  - **The trailer's exception is worth keeping, because the reasoning was sound
    and applied at the wrong width.** It stayed centred on the argument that it
    is sized to its video's aspect ratio while a tray's job is to fill a screen's
    width — true of a desktop. At touch widths a tray *is* the width of the
    screen, so a full-width 16:9 video fills it exactly and there is nothing to
    letterbox against. What a phone actually had was the app's only centred
    overlay, dismissible only by a × in the corner furthest from a thumb.
  - **An overlay's panel never declares its own background, border or radius.**
    The panel is the app's surface wherever it appears. `.modal__panel--video`
    set `background: #000`, which gave the trailer a pure black head beside every
    other overlay's `#2a2a2a` and a per-server accent that stopped at its own
    border. An overlay holding media may paint the **well** the media sits in
    black — a video letterboxes against its container, and letterboxing against
    `--surface` reads as a rendering fault, so that black is a property of the
    medium — but it stops at the well.
    - **A placeholder in that well is opaque and the SAME value as the well.**
      The loading state was `rgba(26, 26, 26, 0.7)`, which composites over black
      to `#121212`. So the two were different blacks with a seam between them,
      and the region changed colour at the instant the video arrived — the
      instant a viewer is looking hardest at it, and the one moment no
      screenshot of a resting overlay can show.
  - **A fixed-ratio box is capped by its WIDTH, never by `max-height`.**
    `max-height` on an `aspect-ratio` box clamps the height while the width goes
    on filling its container, so the ratio breaks and the content letterboxes
    inside its own well. Derive the width from the height budget instead —
    `width: min(100%, calc((88vh - 120px) * 16 / 9))`. It only ever binds on a
    short viewport (a landscape phone, a 700px desktop window), which is exactly
    where nobody looks.
  - **A head title is bounded to one line at the shared rule, by a line clamp
    and not by `white-space: nowrap`.** The trailer is the first head whose title
    is data rather than a constant, and it must be bounded because on touch the
    head is part of the drag region. Nowrap sets a property that
    `.modal__fixed .modal-title` — the detail overlay's deliberate three-line
    title — does not, so it wins everywhere and silently flattens that title to
    one line. A clamp composes: the shared rule states the default, an overlay
    with the room states its own. `min-width: 0` is load-bearing and reads like
    boilerplate: a flex item's default `min-width: auto` refuses to shrink below
    its content, so without it a long title pushes the × out through the side of
    the panel instead of truncating.
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
- **A control crossing between the neutral fill and the accent fill changes BOTH
  ON THE SAME FRAME. Neither is transitioned.** The two fills sit at opposite
  ends of the brightness range, so their labels do too — white on `--tab-bg`,
  black on the accent — which makes them one pair: whenever one arrives without
  the other, the pill wears the wrong label for the whole duration. **A selected
  state is a state, not an animation.** On a tab click the page slide supplies
  the motion; a 300ms pill fade adds nothing a viewer can attribute.
  - **All three orderings shipped, and two of them look like fixes for the
    third.** `transition: all` eased both, so the text crossed mid-grey while
    the pill crossed mid-accent — barely readable on Plex yellow. Easing the
    fill and switching the label was *worse*: deselecting put a fully white
    label on a fully yellow pill on the first frame and held it while the yellow
    drained. That one reached a user. Switching the fill and easing the label is
    the same defect reflected. Contrast is a relation between two properties,
    not a fact about either, so moving one alone only moves the bad window.
  - **A defect that presents in one direction is still present in both.** With
    the fill eased and the label switched, *selecting* put a black label on the
    dark neutral fill — equally illegible, reads as dim rather than wrong, and
    went unreported. Fixing only the half that was reported is what produced the
    second version. Verify selection AND deselection, every time.
  - **`transition: all` is how `color` got into the fade in the first place,
    unwritten.** Name the properties — or, once nothing is left that may move,
    declare no transition at all rather than one naming what the rule does not
    change. The pills' hover tint snaps as a consequence: hover and selection
    share one `background-color`, and CSS cannot tell `.tab:not(.active)`
    reached by hovering from the same state reached by deselection.
  - It is the 300ms that made it a test rather than something a human catches:
    it exists only on the frames between two correct states, so every
    screenshot ever taken of these controls shows them resting and fine.
    `tests/test_pill_contrast.py` pins the source decision — but **its first
    version passed the build that reached the user**, because it encoded the
    spec faithfully and the spec was wrong. A test derived from a spec inherits
    the spec's blind spot. Verify with DevTools animation playback at 10–25%.
- **The media grid renders a WINDOW near the viewport, never the library.** A
  library is data; a grid is a rendering of part of it. Rendering every item tied
  the browser's per-frame cost to how much media a user owns, so the app got
  slower for exactly the people who use it most. Measured at 7,000 movies:
  **63,248 DOM nodes, ~3fps while idle, a 666ms forced relayout every time an
  overlay opened, and 6 cards on screen.** The trays were reported as "choppy"
  because of this — at 3fps a 280ms tray animation gets one frame — and there was
  never anything wrong with the trays.
  - **Nothing may be per-card that can be per-grid.** One delegated click
    listener, not one per item. `IntersectionObserver` sees only rendered cards
    and is told to `unobserve` the ones leaving. No `setTimeout` per card. A
    recycled element must resolve its item through `dataset.index` at click time,
    or it opens the item it used to hold.
  - **An entrance delay is computed within the window and capped.** It was
    `index * 0.03s` over the whole library, so the 7,000th card waited **209.97
    seconds** and 6,611 of 7,000 sat at `opacity: 0`. The grid was not slow to
    animate — most of it was invisible, and scrolling showed empty space where
    cards were. Any per-item delay multiplied by a count the app does not control
    is this bug.
  - **Row geometry is read from the rendered grid, never from a breakpoint.**
    `auto-fill` decides the column count from the width available. Measure from
    the grid's **content** box: it is padded, and using the border box puts every
    row boundary a fifth of a row out.
  - **The spacers that stand in for unrendered rows must span every column**
    (`grid-column: 1 / -1`). Otherwise `auto-fill` lays one out as an ordinary
    cell, every following card shifts a column, and it reads as an off-by-one in
    the window rather than a layout bug.
  - **`make test` cannot check any of this.** CI has no browser and no library,
    and a bound asserted against a small fixture passes whatever the code does —
    it was already true before windowing existed. `tests/test_grid_windowing.py`
    pins the source decisions; `tools/grid_metrics.py` against a library seeded
    to thousands produces the numbers. Both halves, or neither is worth having.
  - **`scroll-behavior: smooth` is set on the document.** Every `scrollTo`
    animates for about a second, so anything measuring a scroll position must
    wait for it to land. Measuring mid-flight reads a position the user never
    occupied, and it looks exactly like a windowing bug — it cost a full
    debugging pass here, and produced a fix for a cause that did not exist.
    - It is also why `scrollPageTo()` takes a `behavior`. The tab transition
      scrolls to the top of the incoming tab *underneath* the slide, so a smooth
      scroll there is still travelling when the animation ends and the page
      drifts to the top a beat later. Measured: still at 3000px two frames in,
      settling at 12px rather than 0.
- **The tab swipe is a drag, and every part of it is measured.** The tabs follow
  the thumb — both 1:1, a full viewport apart — and the release commits,
  abandons, or springs back from a resisted end. **Both** tabs are frozen with `position: fixed` so they leave the
  scroller; the outgoing one at `-scrollY`, the incoming one at 0. The page is
  then set to 0 in the one frame nothing on screen reflects it. That is what
  makes it one movement rather than a jump followed by a slide — both tabs share
  one document scroll, so there is no other way to show the incoming tab's top
  while the outgoing shows where the viewer was.
  - **The tabs are EDGE TO EDGE, never overlapping, and that is a correctness
    decision rather than a look.** A parallax lag was built first — the incoming
    tab a third of a viewport out, at a third of the speed — because that is
    what the platform does. At that distance the two grids overlap for the whole
    gesture, and both carry the same `z-index`, so paint order fell back to
    **document order**: `#tvshows-content` is second in the markup, so TV Shows
    painted over Movies *in both directions*. It reached the user as "the TV
    show grid is always on top". A full viewport apart, the question cannot
    arise. There is no ratio token — pinned at 1 it would be a knob that does
    nothing. The two panels tile the viewport: each is exactly one viewport
    wide, so there is no gap between them at any offset either.
  - **Freezing BOTH is what makes the gesture abandonable.** The earlier version
    froze only the outgoing tab and reset the page immediately, which is fine for
    a transition that always completes. A drag can be let go of, and a page
    already at 0 has discarded the offset it must return to. The abandon path
    restores it in `endTabTransition()`, after un-pinning, in the same
    synchronous block — un-pinning first puts the page at the top of the library,
    so a paint between the two shows the viewer row 0 for a frame.
  - **The setup cost is the RENDER, not the library.** This was measured wrong
    once and the wrong model survived into a design. Filter and sort over 7,000
    items is 16.9ms; `displayMedia()` is 147.9ms and costs the same at 1,200
    items. So the lever is not rendering at all: each grid view carries a
    `renderSignature()` — tab, search, genre, sort, length — and the render is
    skipped when it still matches. **175.3ms → 1.4ms.** The inactive tab is
    re-warmed at idle whenever the selection changes so that skip actually hits.
    - The signature is `JSON.stringify`, not a delimiter join. Search term and
      genre both admit spaces, so `"a b"`/`"c"` and `"a"`/`"b c"` join
      identically — a collision in the one direction this must never be wrong
      in. A false "stale" costs a render; a false "current" shows the viewer the
      other selection's grid, which is this project's oldest failure.
  - **The freeze reads NO geometry.** Setting the frozen styles costs 0.2–0.4ms;
    a single `getBoundingClientRect()` afterwards costs **77.7ms**, landing on
    the animation's first frame. `tests/test_tab_transition.py` bans the whole
    family — `offsetHeight`, `getComputedStyle`, all of it — because the symptom
    is "the slide is janky" and the transform is what gets blamed.
  - **The transform is never the cost, and the layer size is not the axis.** A
    `translateX` on a box 1,228,722px tall holds 59.9fps with zero dropped
    frames. Bounding it to `100vh` changes neither the frame rate nor the
    scrollable overflow — that mitigation was proposed, measured, and dropped.
  - **The slide starts two rAFs after the render, not one.** A rAF callback runs
    *before* that frame's layout and paint, so one frame puts a fresh 120-card
    grid's layout on the animation's opening frame: **183.4ms of a 280ms
    slide**, with every frame after it a clean 16.7ms. Likewise `will-change`
    belongs on the frozen and parked states, not on the sliding one, or layer
    promotion is paid on the same frame.
  - **A tab arriving on a slide does not also stagger its cards.** The entrance
    fade softens a grid appearing *in place*; a tab crossing the viewport is
    already a soft arrival, and the stagger was the largest cost on that frame.
  - **Horizontal translate only. There is no exception, and there was one.**
    `firstVisibleRow()` reads `getBoundingClientRect().top`, so a `translateY` —
    or a scale — re-windows the grid mid-flight against a position the viewer
    never occupied. `updateGridWindow()` therefore **refuses outright** while a
    gesture is live. Do not substitute the fact that a pinned tab receives no
    scroll events: that is a consequence of the freeze, not a rule anyone
    stated. The refusal predates the lift and outlives it.
  - **The pinned tabs are offset by `contentTop`, never by `-scrollY` alone.**
    `.content` starts below the header, and the header shrinks on scroll so it
    is not a constant to hardcode. `beginTabTransition()` therefore takes one
    `getBoundingClientRect()` — **before any write in that function**, against
    layout the browser already computed, which is free. The ~78ms rule is *never
    measure what you just invalidated*, not *never measure*; the test enforces
    the ordering rather than banning the call.
  - **The axis locks at 8px, and that is not the commit distance.** They were one
    number and that is why nothing could move until the finger lifted: the old
    handler claimed the gesture only after 100px. Nothing can move before the
    claim, and on iOS a sequence whose early moves went uncancelled has already
    gone to the scroller, where later `preventDefault()` is ignored. The
    `touchmove` listener is non-passive **from the start** for the same reason.
    Commit is a third of the viewport **or** a flick, read from the last ~100ms
    rather than the gesture's average, and it is never latched — out past the
    threshold and back is an abandon.
  - **A drag is refused at `touchstart`, and it asks the overlay system.** A
    discrete gesture could check at the end because nothing had moved; a drag
    that discovers the conflict later has already pinned two tabs. It calls
    `window.GlimpseOverlays.anyOverlayOpen()` rather than naming overlay keys —
    a name list is a registry by another route, and the DOM-keyed rule at the
    top of `overlays.js` is exactly what it exists to avoid.
  - **`touchcancel` is bound, and it matters more than it did.** An incoming call
    mid-drag must not leave two tabs pinned and the grid refusing to re-window:
    that is a page that will not scroll, with nothing on screen to explain it.
  - **The drag is gated on `isMobile`, the gesture's own flag — never a media
    query.** Same pairing rule as the affordances: two conditions describing one
    capability drift, and this repo has already shipped a pair that reached 992px
    and 768px independently.
  - **A dragged tab is MOVED, and nothing else is done to it.** Four ways of
    raising it were tried; all four are gone, and the one that shipped is the
    reason this is now a rule rather than a preference.
    - **The scale is what a user finally reported, as "the grid drops down".**
      A `scale(0.94)` anchored to the viewport's midpoint pulls everything above
      that midpoint toward it — **~23px on a phone**, arriving with no easing
      the instant the gesture is claimed and reversing on release. Vertical
      motion in a gesture that means nothing but horizontal does not read as
      depth; it reads as the page malfunctioning, and it lands *before* any
      horizontal travel, so it is the first thing seen.
    - **It shipped twice broken, and the first one is the sharper lesson.**
      `transform-origin` defaults to the element's own centre, and a tab holding
      7,000 items is 1,227,442px tall — so scaling about a point ~600,000px
      below the screen threw the first card **+36,791px** downward. The
      displacement scaled with library size, so the 7,000-item tab vanished
      while the 1,200-item one barely moved, and it reported as *"it always
      shows the TV Shows grid whichever way I swipe"* — a routing bug that did
      not exist. One cause, two symptoms, and the plausible one was wrong.
      Anchoring the origin to the viewport bounded that to the 23px above.
    - **A moved rect is an arithmetic hazard AND a visible one.** The windowing
      refusal was in place and correct throughout and did nothing for either
      symptom. Reasoning about a transform only in terms of what it does to the
      *maths* is how the far larger problem — what it does to the *picture* —
      went unconsidered, twice.
    - **The scrim went with the scale, because it had nowhere left to render.**
      Each panel is one viewport wide, so unscaled the pair tiles the screen at
      every offset and a dim behind them is covered on every frame. Kept, it
      would be a full-screen fixed element that can never be seen — live code
      that cannot succeed, which is the shape this repo has shipped twice.
    - **The shadow and the radius never shipped, for the reason to hold first
      about these panels:** they are as tall as the whole library and pinned at
      the captured offset, so only one viewport of one is ever on screen and
      neither of its ends is. A `box-shadow` renders solely as a blurred band
      down each vertical edge tracking the thumb; a radius renders nothing
      whatsoever. Their height is the first thing to reason from, not the last.
  - **The first-load swipe tip stays.** It was removed on the argument that a
    drag demonstrates itself; it only demonstrates itself to someone who already
    tries it, and the gesture has no visible affordance at rest. What is gone is
    the *post-commit* toast naming the tab arrived at — the motion says that,
    and says the direction too.
  - **`transform !== 'none'` does not prove a transition ran.** It is satisfied
    by the *start* value, so it passes for a slide that never moves — and it
    did, in the first version of this verification. Movement does not begin
    until ~85ms after the class lands. Sample the path across frames, not a
    point. **For a drag the bar is higher still:** the proof is that the
    transform *corresponds to the finger*, because a handler writing a constant
    offset on the first move passes any single-point check ever written. Drive
    a known path with `Browser.drag()` and assert against each coordinate,
    including a reversal.
  - **Do not measure a gesture with a harness that runs inside the frames it is
    timing.** Dispatching synthetic `TouchEvent`s from the rAF callback that
    records frame gaps reported a 33.4ms median; the real CDP input path on the
    same build reports 16.7ms. It is the forced-layout trap in another costume.
    And always run a control at the same dispatch rate with the gesture *not*
    claimed — over CDP the driver's blocking round-trips drop as many frames as
    the drag does, so without one the tail cannot be attributed to anything.
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
