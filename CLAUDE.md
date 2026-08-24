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

- **The entrypoint validates the environment and writes `/app/web/config.json`.
  It never edits web assets.** The old entrypoint rewrote `index.html` with `sed`
  at boot — per-server themes, an injected server dropdown, and a set of
  "repair the file we corrupted" functions to clean up after itself. That is the
  single largest source of past bugs in this project and it is not coming back.
  Per-server theming is `data-server="jellyfin"` on `<html>` plus CSS custom
  properties. If a behavior seems to need the entrypoint to touch a file under
  `/app/web` other than `config.json`, it is a spec change to
  `application-shell`, not a wiring decision.
- **The frontend reads `config.json` once at boot into a single store.** Never
  re-read it, and never add a second source for a setting. The environment is
  read by the entrypoint and by nothing else.
- **Emby and Jellyfin are one adapter with two identities**, not two code paths —
  their APIs are compatible, which is why one fetcher already serves both. A fix
  applied to one that isn't applied to the other is a bug, and the reason
  library-exclusion had to be fixed twice.
- Artwork is re-downloaded only when its MD5 changes. The checksum store is
  per-server and lives on the mounted volume, so a first run after an upgrade
  must not invalidate it — that would re-download an entire library.
- **An overlay is a tray**: a bottom sheet on phones, a centered dialog on
  desktop. It declares `role="dialog"` and `tabindex="-1"`, and **nothing else
  makes it focus-managed** — the manager finds its subjects by that attribute, so
  an overlay added without the role opens and leaves a keyboard user on the page
  behind the backdrop with no way in.
  - **A control that closes its own tray and opens another must move focus to
    something still on screen before the first one hides.** Alpine hides on the
    flush *after* the handler, and hiding a focused element hands its focus to
    `<body>` — which the focus manager reads a frame later to decide where to
    return focus to, and an origin rooted at the body is the one case it declines
    to restore. The overlay opens correctly and dismissing it drops the keyboard
    user at the top of the page. Nothing errors, and the pointer path looks
    perfect. Call the opening control's `.focus()` first.
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
