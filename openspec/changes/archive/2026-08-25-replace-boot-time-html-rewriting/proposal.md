## Why

`config/entrypoint.sh` is 1,915 lines of shell that rewrites the application's
HTML with `sed` on every container start. It injects per-server themes, retitles
the page, repoints every data path, copies `index.html` into `/plex/`,
`/jellyfin/` and `/emby/` sub-routes, swaps a two-server toggle button for a
three-server dropdown, and then runs `cleanup_duplicate_server_content()` and
`fix_corrupted_files()` to repair the damage it did to its own output.

Those last two functions are the whole argument. A boot script that ships with a
repair pass for its own corruption is not configuring an application, it is
fighting one. Every past bug in server switching, theming, and library selection
traces back to a `sed` expression matching something it should not have, or
matching nothing at all and failing silently — because `sed` cannot tell the
difference between "the pattern is absent" and "the pattern already ran". The
script is also not idempotent in the way it needs to be: it mutates files that
persist in the image layer, so a restart re-applies substitutions to
already-substituted text.

This is the change that has to come first. Every other planned rewrite —
the frontend, the fetchers — needs a settled answer to "how does the app learn
what it was configured with", and today that answer is "it is compiled into the
markup at boot".

## What Changes

- **The entrypoint stops editing authored files.** It generates
  `/app/web/config.json` and `/app/web/manifest.json`, and touches nothing else
  under `/app/web`. The distinction that replaces the old rule is *generate,
  never mutate*: a file the entrypoint writes in full is fine, a file it patches
  in place is not.
- **`config.json` becomes the container-to-frontend contract.** It carries the
  app title, the resolved primary server, the list of configured servers, the
  default sort, and each server's data path.
- **Per-server theming moves to `data-server` on `<html>` plus CSS custom
  properties.** No injected `<style>` block, no `!important` cascade, no
  per-server copies of the page.
- **The `/plex/`, `/jellyfin/` and `/emby/` sub-routes stop being duplicated
  HTML files.** nginx serves the same `index.html` for all of them; the app
  reads the server from the path. The URLs keep working — users have bookmarked
  them — but there is one page instead of four.
- **~1,700 lines of shell are deleted**, including `apply_jellyfin_theme`,
  `apply_emby_theme`, `create_themed_offline`, `create_server_index`,
  `replace_toggle_with_dropdown`, `cleanup_duplicate_server_content`,
  `remove_server_toggle` and `fix_corrupted_files`.
- **The existing `index.html` gets a small, deliberately temporary adapter** —
  roughly eighty lines that read `config.json` and apply what `sed` used to bake
  in. It is throwaway: the frontend rewrite replaces the file wholesale. It
  exists so this change is independently shippable and testable on `:dev`
  instead of being welded to a frontend rewrite that would then have no settled
  contract to build against.
- **Emby is fixed in the server switcher.** `toggleServer()` currently hardcodes
  a Plex↔Jellyfin swap and falls through to a placeholder for any other pairing,
  so a Plex+Emby install cannot switch back. Config-driven switching removes the
  hardcoded pair.
- **The CI smoke test gains its readiness assertion** — `config.json` is the
  evidence the boot script finished, which liveness on `/` cannot show.

**No BREAKING changes.** `docker-compose.yml` is untouched, every environment
variable keeps its current meaning and defaults, and the sub-route URLs still
resolve.

## Capabilities

### New Capabilities

- `application-shell`: How the container boots — environment validation, the
  `config.json` contract, cron installation, nginx routing, and the rule that
  the entrypoint generates files rather than mutating authored ones.
- `multi-server`: Detecting which servers have credentials, resolving
  `PRIMARY_SERVER` (including correcting one that names a server with no
  credentials), the sub-route URLs, switching between servers, and the
  per-server theme that follows the choice.
- `pwa`: The generated manifest, its per-server icons and colors, the service
  worker's cache behavior across a server switch, and the offline page.

### Modified Capabilities

None. `openspec/specs/` is empty — this is the first change in the repo, so
every capability it touches is being specified for the first time.

## Impact

**Code**

- `config/entrypoint.sh` — rewritten, ~1,915 lines to roughly 200.
- `config/nginx.conf` — sub-route locations serve the single `index.html`.
- `web/index.html` — temporary config-reading adapter; per-server theme tokens.
- `web/manifest.json` — becomes a generated artifact; the checked-in file is the
  Plex-themed default so the repo still serves without a container.
- `web/sw.js` — cache keyed per server so a switch does not serve the previous
  server's page.
- `web/offline.html` — themed by the same tokens instead of being regenerated.
- `.github/workflows/ci.yml` — add the `config.json` readiness assertion.
- `tests/` — new coverage for server resolution and the generated config.
- `CLAUDE.md`, `docs/docker.md` — restate the entrypoint rule as *generate,
  never mutate*, which is broader and more accurate than the current
  "only `config.json`" wording.

**Behavior preserved exactly**

Every environment variable and its default; the `PRIMARY_SERVER` auto-correction
and its warning messages; the `"<title> - <Server>"` page titles; the toggle for
two servers and dropdown for three; the per-server palettes
(Plex `#e5a00d`/`#f1b020`, Jellyfin `#00a4dc`/`#0288c2`, Emby `#52c41a`/`#389e0d`);
the sub-route URLs; and the failure to start when no server has credentials.

**One open question, flagged not decided**

The generated manifest's `theme_color` currently maps Jellyfin→`#101010`,
Emby→`#0f1419`, Plex→`#131313`. The blue-tinted `#0f1419` sitting on Emby (a
green-branded server) while Jellyfin (blue-branded) gets a neutral `#101010`
looks like a transposition rather than a decision. The design phase records it;
it is preserved as-is unless the user says otherwise.

**Risk**

The sub-route change is the sharp edge. Anyone who bookmarked
`http://host:9090/jellyfin/` must still land on a working Jellyfin view, and the
service worker may hold a cached copy of the old per-server page — which is why
cache keying is in scope rather than deferred.
