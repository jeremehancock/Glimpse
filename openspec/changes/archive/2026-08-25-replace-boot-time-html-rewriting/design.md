## Context

The container boots by running `sed` over `/app/web/index.html` about eighty
times. The substitutions fall into five groups:

| What `sed` does today | Lines |
| --- | --- |
| Retitle the page and the `<h1>`, apply `APP_TITLE` | ~1730–1740 |
| Repoint `data/movies.json` → `data/<server>/movies.json`, and the poster and backdrop directories | ~1745–1790 |
| Inject a per-server `<style>` block of `!important` overrides and repoint every icon to `images/<server>/` | 504–884 |
| Copy the page into `/plex/`, `/jellyfin/`, `/emby/` and rewrite every relative path to `../` | 1013–1090 |
| Replace the two-server toggle markup with a three-server dropdown | 1138–1707 |

Then `cleanup_duplicate_server_content()` and `fix_corrupted_files()` run to
undo the damage. That pairing is the diagnosis: the script has no model of the
document, so it cannot distinguish "this pattern has not been applied yet" from
"this pattern was applied on the previous boot". Restarting a container
re-substitutes already-substituted text, which is why the repair functions had to
exist at all.

Two properties of `sed` make this unfixable rather than merely buggy. It fails
**silently** when a pattern does not match — an edit to the markup that a
substitution depended on breaks configuration with no error, at runtime, in
production. And it is **not idempotent** over its own output, so correctness
depends on the number of times the container has started.

Constraints that shape everything below:

- `docker-compose.yml` is frozen. Same variables, same meanings, same defaults.
- The sub-route URLs (`/plex/`, `/jellyfin/`, `/emby/`) are bookmarkable and must
  keep resolving.
- Nothing in `web/` may acquire a build step. nginx serves it as authored.
- Every visible behavior is preserved. This change is invisible to a user who is
  not reading the container logs.

## Goals / Non-Goals

**Goals:**

- One authored `index.html`, served for every route, configured at runtime.
- A single declared contract between container and frontend, in a format that
  fails loudly (`config.json`) rather than silently (a missing `sed` match).
- Boot behavior that does not depend on how many times the container has
  started.
- Delete the repair functions by removing what they repair.
- Leave the frontend rewrite a settled contract to build against.

**Non-Goals:**

- Restructuring the frontend. The grid, detail modal, search, sort, genre
  filter, trailer and roulette code are untouched beyond the adapter.
- Restructuring the Python fetchers. Separate change.
- Changing the on-disk snapshot layout, and in particular `checksums.pkl` —
  invalidating it turns the next scheduled run into a full re-download of every
  poster in the library.
- Adding authentication, or any write path to a media server.

## Decisions

### 1. The entrypoint generates files; it never mutates authored ones

The rule in `CLAUDE.md` currently reads "never edit a file under `/app/web`
other than `config.json`". That is too narrow — `manifest.json` also has to be
produced per-server, and a manifest cannot reference a CSS custom property, so
it genuinely must be written at boot.

The accurate line is **generate, never mutate**. A file the entrypoint writes in
full, from a template it owns, is fine: it is deterministic, its content does not
depend on prior boots, and reading it tells you exactly what the container
decided. A file the entrypoint patches in place is not, for the reasons above.

So: `config.json` and `manifest.json` are generated. `index.html`, `sw.js`,
`offline.html` and everything under `images/` are authored and read-only at
runtime. `CLAUDE.md` and `docs/docker.md` are updated to this wording as a task
of this change.

*Alternative considered:* keep a single generated `config.json` and have the app
inject the manifest via a Blob URL at runtime. Rejected — install prompts and
icon resolution behave inconsistently across browsers when the manifest is not a
real URL, and it trades a well-understood generated file for a subtle one.

### 2. `config.json`, fetched once, is the whole contract

```json
{
  "appTitle": "Glimpse",
  "primaryServer": "plex",
  "servers": [
    { "id": "plex",     "name": "Plex",     "dataPath": "data/plex" },
    { "id": "jellyfin", "name": "Jellyfin", "dataPath": "data/jellyfin" }
  ],
  "sortByDateAdded": false
}
```

`servers` is an array of objects rather than a list of ids because the frontend
needs the display name and the data path anyway, and deriving them client-side
would put the mapping in two places. It is ordered `plex, jellyfin, emby` — a
fixed order, so the switcher's entries do not reshuffle when a user adds a
server.

The file is fetched once at boot and read into one store. It is never re-fetched:
configuration cannot change without a container restart, and a second read is
just an opportunity for two parts of the app to disagree.

**Why a fetched file and not an inlined `<script>` block.** Inlining would mean
generating `index.html`, which is the thing being removed. A separate file keeps
the page authored and cacheable, and gives the CI smoke test something to assert
on — which is the difference between proving the container is alive and proving
it is configured.

**Failure is loud.** If `config.json` is missing or malformed the app renders an
error naming the file, rather than silently falling back to defaults. A silent
fallback here reproduces exactly the failure mode being removed: a
misconfiguration that looks like a working app showing the wrong library.

### 3. Theming is `data-server` plus CSS custom properties

`<html data-server="jellyfin">`, set from `config.json` before first paint, with
the palettes stated once in the stylesheet:

```css
:root[data-server='plex']     { --primary-color: #e5a00d; --primary-hover: #f1b020; }
:root[data-server='jellyfin'] { --primary-color: #00a4dc; --primary-hover: #0288c2; }
:root[data-server='emby']     { --primary-color: #52c41a; --primary-hover: #389e0d; }
```

This deletes the injected `<style>` blocks and, with them, every `!important`.
Those existed only to out-rank the stylesheet they were appended to — a problem
that does not exist once the theme is a variable the stylesheet already reads.

Per-server icons are the one case a custom property cannot express, since `<link
rel="icon">` needs a real `href`. The adapter rewrites those few `href`s from
`config.json` at boot. That is DOM manipulation by the app, not `sed` over a
file: it is idempotent, it operates on a parsed document, and it leaves nothing
on disk.

**The attribute is set before first paint**, in a small inline script in
`<head>`, not after `DOMContentLoaded`. Setting it later means the page paints
in the Plex palette and then flips — a visible flash of the wrong brand on every
load for two-thirds of users.

*Alternative considered:* `prefers-color-scheme`-style separate stylesheets per
server. Rejected — three near-identical files to keep in sync, and a second
network round trip before first paint.

### 4. Sub-routes are nginx aliases, not copies

```nginx
location ~ ^/(plex|jellyfin|emby)/?$ {
    try_files /index.html =404;
}
```

One file serves every route. The app reads the leading path segment, and when it
names a configured server that becomes the active one; otherwise the active
server is `primaryServer`. This is what removes `create_server_index()` and its
forest of `../` path rewrites.

**Relative paths are why the copies existed, and they are the trap here.**
`/jellyfin/` has a different base than `/`, so `data/plex/movies.json` resolves
differently for each. The old script solved that by rewriting every path to
`../`. The fix is to resolve data paths against an absolute root (`/data/...`)
rather than the document — one rule, no per-route variants.

*Alternative considered:* a query parameter (`/?server=jellyfin`). Cleaner, but
it breaks every bookmark, and the sub-route URLs are documented in the README.

### 5. The service worker caches per server

The service worker currently caches one copy of `/index.html`. With one file
serving four routes, a stale entry can hand a user the previous server's view
after a switch — the reason `toggleServer()` already posts a
`CLEAR_THEMED_CACHE` message today.

The cache key gains the active server. A switch then reads a different key rather
than racing a cache-clear against a navigation, and the message handler is
retired. The cache version string also changes in this release, so the first load
after upgrading discards anything cached against the old scheme.

### 6. `PRIMARY_SERVER` resolution is preserved exactly, and moved into Python

The auto-correction is genuinely useful behavior — `PRIMARY_SERVER=plex` with
only Jellyfin credentials switches to Jellyfin and warns — and its warning
strings appear in support threads. Preserved verbatim, including the two error
messages and the non-zero exit when no server has credentials.

The logic moves from ~70 lines of nested shell into a small Python module the
entrypoint invokes to produce `config.json`. Python because it is already in the
image, it can write JSON without quoting hazards, and — the actual reason — it
can be unit-tested. The resolution table is the highest-traffic conditional in
the project and currently has no test at all.

The shell keeps what shell is good at: checking the environment, installing the
crontab, creating directories, starting supervisord.

### 7. The legacy `index.html` gets a temporary adapter

Roughly eighty lines that read `config.json` and apply what `sed` used to bake
in: the title, the `<h1>`, the data path prefix, the default sort, the icon
`href`s, and the switcher's entries.

It is throwaway — the frontend rewrite replaces the file. Writing it anyway buys
the thing that matters most here: this change ships and gets validated on `:dev`
**on its own**, so if server switching breaks, the cause is a 200-line entrypoint
and not a simultaneous 4,000-line frontend rewrite. Bundling them would produce
exactly the debugging problem this project already has.

The adapter is marked in-file with the change name that removes it.

## Risks / Trade-offs

**A bookmarked `/jellyfin/` breaks** → The sub-route contract is specified and
tested. `make docker-smoke` is extended to request each configured server's route
and assert the response carries that server's data path.

**A stale service worker serves the pre-upgrade page** → The cache version
changes, so the first post-upgrade load discards the old entries. This is worth
calling out in the release notes regardless: a PWA user may need one reload.

**`checksums.pkl` is invalidated and every poster re-downloads** → Nothing in
this change touches the snapshot layout, the id scheme, or the fetchers. Stated
as a non-goal because it is the most expensive mistake available in this repo,
and the temptation to "tidy the data directory while we are in here" is real.

**A `sed` substitution encoded behavior nobody wrote down** → 1,915 lines of
shell accreted over years, and the proposal's preserved-behavior list was built
by reading it rather than from a spec. Mitigated by specifying each behavior as a
scenario, and by validating on `:dev` against a real multi-server install before
archiving. Residual risk is real and accepted; this is the argument for shipping
it separately from the frontend rewrite.

**The adapter is wasted work** → About eighty lines, deleted in the next change.
Accepted deliberately: it is the price of two independently debuggable releases,
and it is cheap next to the ~1,700 lines it retires.

**Python at boot adds a failure mode shell did not have** → An exception while
generating `config.json` must exit non-zero with a readable message, not leave a
half-written file. The generator writes to a temporary path and renames, so a
partial file is never served.

## Migration Plan

No user action. The entrypoint runs on the existing volume, the snapshot layout
is unchanged, and a downgrade to the previous image works because nothing on disk
has changed shape — the generated files live in the image's `/app/web`, not in
the mounted `/app/data`.

1. Rewrite the entrypoint and add the Python config generator, with tests.
2. Add the nginx sub-route locations.
3. Add the theme tokens and the adapter to `index.html`.
4. Key the service-worker cache per server.
5. Extend `make docker-smoke` and the CI smoke test to assert readiness.
6. Validate on `:dev` against an install with at least two servers configured,
   exercising both the toggle and a direct sub-route URL.

Rollback is `image: bozodev/glimpse-media-viewer:1.3.0` in the compose file.

## Open Questions

1. **The manifest `theme_color` mapping looks transposed.** Today: Jellyfin
   `#101010`, Emby `#0f1419`, Plex `#131313`. A blue-tinted `#0f1419` on
   green-branded Emby while blue-branded Jellyfin gets neutral `#101010` reads as
   a swap rather than a decision. Preserved as-is unless corrected — it is
   cosmetic, it affects only the PWA splash and the mobile address bar, and
   "preserve every behavior" is the stated constraint. Flagged for the user.

2. **Should an unconfigured sub-route 404 or redirect?** Requesting
   `/emby/` on a Plex-only install currently 404s, because the file was never
   created. Under nginx aliases it would serve the app, which then finds no such
   server. Specified as a redirect to `/` — a bookmark surviving a config change
   is friendlier than a dead end — but a 404 is defensible and reversible.
