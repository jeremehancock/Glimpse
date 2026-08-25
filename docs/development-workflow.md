# Development workflow — Claude Code, OpenSpec & releases

> **Mid-rewrite.** See [handover.md](handover.md) for what has shipped to `dev`,
> what is unfinished, and why `:dev` is currently built by hand. Read it before
> acting on the release flow described below.

How Glimpse is developed: the **`dev` branch for feature work and testing**,
**`main` for releases**, with every capability specified before it is built.

---

## Branches & Docker image tags

CI publishes to Docker Hub automatically (see
`.github/workflows/docker-publish.yml`):

| You push to… | Docker Hub tag | Use for |
| --- | --- | --- |
| `dev` | `bozodev/glimpse-media-viewer:dev` | testing new work on a throwaway instance |
| `main` | `bozodev/glimpse-media-viewer:latest` | production (always the latest) |
| `main`, when `VERSION` names an unreleased version | also `bozodev/glimpse-media-viewer:<version>` | pinned releases |

`main` is **always** `:latest`. A **versioned release happens automatically**:
when a push to `main` carries a `VERSION` that hasn't been released yet, CI also
publishes the pinned image and creates the matching `v<version>` git tag +
GitHub Release. Every build also gets an immutable `sha-<short>` tag.

**Publishing waits for a green CI.** The publish workflow runs only *after* the
CI workflow (lint, tests, and the image smoke test) succeeds for that commit. A
failing or cancelled CI publishes nothing. CI is **push-only** — pull requests
don't trigger it, so each commit is built exactly once (its status still shows on
the PR, because checks attach to the commit SHA). A `workflow_dispatch` entry
exists so the publish can also be run by hand from the Actions tab, deliberately
skipping the CI gate.

> **None of the publishing above is live yet.** GitHub registers both
> `workflow_run` and `workflow_dispatch` only for a workflow file present on the
> **default branch**, and `main` currently has no `.github/workflows/` directory
> at all — so `docker-publish.yml`, which lives on `dev`, is not registered and
> has never fired. The Actions-tab override cannot rescue it for the same reason.
> Build `:dev` by hand until the workflows land on `main`; see
> [handover.md](handover.md).
>
> Expect one wrinkle when they do: putting the file on `main` is what registers
> the trigger, so the merge that lands it may not publish for its own CI run.
> Check Docker Hub afterwards and push that first image manually if needed.

**The loop:** build on `dev` (CI publishes `:dev`) → test the `:dev` image →
**bump `VERSION` on `dev`** → open a PR from `dev` into `main`. Merging publishes
`:latest` **and** the pinned `:<version>` in one step.

### The version floor

Docker Hub carries tags up to **`1.3.0`** from years of manual `docker build`
runs. This repo has **no git tags at all** — the release workflow is new, and
nothing before it ever created one.

So `VERSION` reads `1.3.0` to describe what is published, and **the first release
cut through CI must bump past it.** If `VERSION` is still `1.3.0` when a PR
merges to `main`, the workflow finds no `v1.3.0` git tag, concludes the version
is unreleased, and publishes `bozodev/glimpse-media-viewer:1.3.0` over the
existing image — different code under a tag someone may have pinned.

`/ship` checks for this before opening a release PR. Don't route around it.

### A separate instance for testing `:dev`

Run a second container from the `:dev` tag, on its own port and its own data
directory, so testing never touches your real instance:

```yaml
services:
  glimpse-dev:
    image: bozodev/glimpse-media-viewer:dev
    container_name: glimpse-dev
    ports:
      - '9091:80'
    volumes:
      - ./glimpse-dev/data:/app/data
    environment:
      - PRIMARY_SERVER=plex
      - PLEX_URL=http://192.168.1.10:32400
      - PLEX_TOKEN=your-plex-token
      - CRON_SCHEDULE=0 */6 * * *
      - TZ=UTC
    restart: unless-stopped
```

Pull the newest dev build and restart with:

```bash
docker compose pull glimpse-dev && docker compose up -d glimpse-dev
```

> Give the test instance its **own** `./glimpse-dev/data` directory. Pointing it
> at your real one lets a broken fetcher overwrite a good snapshot, and the first
> run then re-downloads the whole library to repair it.

---

## Part 1 — Set up the toolchain

### Prerequisites

- **Python 3.13+** — the fetchers and their tests
- **Node 18+** — ESLint and Prettier only. Nothing in `web/` is built or
  bundled; nginx serves those files exactly as authored, and no Node runs in the
  image.
- **Docker** — for `make docker-smoke`
- **Node 18+ and Git** — for the Claude Code and OpenSpec CLIs

Install everything:

```bash
make install        # ruff, pytest, pyyaml, requests + npm ci
```

### Sanity-check the gates

```bash
make lint           # ruff check + ruff format --check + eslint + prettier --check
make test           # pytest
make check          # both
make fmt            # apply every fix lint would ask for
```

Keep these green — CI runs the same on every push.

> If `ruff` isn't on your PATH after `make install`, install it standalone:
> `pipx install ruff`.

### Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude              # first run walks you through signing in
```

Run `claude` from your editor's integrated terminal inside the repo — it picks
up `CLAUDE.md`, the `.claude/` commands, and the OpenSpec context automatically.

---

## Part 2 — OpenSpec in this repo

### What's already set up

- **`openspec/`** — `config.yaml` holds the project context, the **capability
  map**, and per-artifact rules that guide AI-generated specs.
  `openspec/specs/` is the source of truth once changes are archived;
  `openspec/changes/` holds in-flight proposals.
- **`.claude/commands/opsx/`** — the OpenSpec slash commands, committed to the
  repo: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:update`,
  `/opsx:sync`, `/opsx:archive`.
- **`.claude/commands/ship.md`** — `/ship`, the release state machine.
- **`CLAUDE.md`** — loaded into every Claude Code session automatically.

### Install the OpenSpec CLI

```bash
npm install -g @fission-ai/openspec
openspec --version      # this repo was set up against 1.6.0
```

### The mental model

```
idea ─▶ /opsx:explore ─▶ /opsx:propose ─▶ (review) ─▶ /opsx:apply ─▶ /ship ─▶ /opsx:archive
             (think)        (write spec)      (you)      (build code)          (fold into specs)
```

A **change** lives under `openspec/changes/<name>/` and contains `proposal.md`
(why/what), `design.md` (how), `tasks.md` (checklist), and
`specs/<capability>/spec.md` (the delta — `## ADDED/MODIFIED/REMOVED
Requirements`, each with `### Requirement:` and `#### Scenario:` using **exactly
four** `#`). Archiving folds those deltas into `openspec/specs/`.

**A change must target a capability that already exists in the map** in
`openspec/config.yaml` — `media-fetch`, `media-browsing`, `visual-design`, and so
on. Never invent a capability named after the change itself.

### The slash commands

| Command | Use it to… |
| --- | --- |
| `/opsx:explore` | Think through an idea before committing to a change. No code. |
| `/opsx:propose` | Create a new change and generate all its artifacts. |
| `/opsx:apply` | Implement the tasks from a change (writes code). |
| `/opsx:update` | Revise an existing change's artifacts and keep them coherent. |
| `/opsx:sync` | Sync a change's delta specs into the main specs without archiving. |
| `/opsx:archive` | Finalize a completed change and fold its deltas into the specs. |
| `/ship` | Everything after `apply`: gates, commit, archive, PR, resync. |

Reach for `/opsx:propose` by default. `/opsx:explore` earns its cost when you
can't yet state what should be true once the work is done. For a bug with a
known-correct behavior, propose straight away and correct the artifacts with
`/opsx:update` if they miss.

### The raw CLI

```bash
openspec list                       # active changes + task progress
openspec show <change>              # view a change
openspec validate <change> --strict # verify structure (spec deltas, scenarios)
openspec archive <change>           # archive an implemented change
```

Always run `openspec validate <change> --strict` before coding — it catches
malformed spec deltas, most commonly scenarios that don't use exactly four `#`.

### Traps that cost real time

**In a `MODIFIED` requirement, never rename a scenario.** The `#### Scenario:`
header is its identity — `openspec archive` compares headers against the current
spec and refuses the archive, reporting a dropped scenario. Reword the body
freely; keep the header byte-identical, and add new scenarios rather than
repurposing old ones.

**Overturning half a requirement means `REMOVED` + `ADDED`, not `MODIFIED`.**
Because a scenario cannot be dropped or repurposed, a requirement covering two
concerns that later diverge has to be retired whole — with `**Reason**` and
`**Migration**` — and the surviving half re-added under its own name.

**Cron expressions cannot appear in a `/* */` block comment.** `*/6` contains the
character pair that closes one. `CRON_SCHEDULE` defaults to `0 */6 * * *`, so
this comes up in JS and CSS comments constantly. Use `//`, or describe the
schedule in words.

**`docker-compose.yml` is frozen and under test.**
`tests/test_compose_surface.py` asserts its environment variable list exactly, in
both directions — a *new* variable fails it just as a removed one does. See the
frozen-compose section of [CLAUDE.md](../CLAUDE.md).

**Excluding a file from a linter is a checklist entry, not a carve-out.** Both
`pyproject.toml` (ruff `extend-exclude`) and `.prettierignore` /
`eslint.config.mjs` carry entries for the legacy single-file app. Each is deleted
along with the file it names. Nothing new goes on those lists — a new file that
can't pass the gate isn't ready to commit.

---

## Promoting & releasing

Releases are driven by the **`VERSION` file**, and everything happens on the
`dev → main` merge — no manual tagging.

- `main` is **always** `:latest`. Every merge to `main` refreshes it.
- If the merge carries a **new** version (a `VERSION` value with no matching
  `v<version>` tag yet), CI *also* publishes the pinned image and creates the
  `v<version>` git tag + GitHub Release.
- Merge to `main` **without** changing `VERSION` → just `:latest`.

So a release is: **bump `VERSION` on `dev`, then merge `dev` → `main`.**

### Release checklist

```
[ ] Feature validated against the :dev image
[ ] VERSION bumped on dev + pushed             → :dev rebuilt at the new version
[ ] Change archived (specs updated)            → code and specs ship together
[ ] dev → main PR merged                       → :latest + :<version>, tag + Release
[ ] dev synced with main
```

`/ship` walks this list for you and will not skip the bump. Leaving `VERSION`
equal to the latest tag is the quiet failure to watch for: the merge still
publishes `:latest`, so nothing looks wrong, but no pinned image, tag, or
GitHub Release is created.

### Keeping `dev` in sync after a merge

```bash
git checkout dev && git fetch origin && git merge --ff-only origin/main && git push
git fetch origin main:main    # refresh the local main ref without checking it out
```

Merge `origin/main`, **not** `main`. This workflow never checks out `main` — PRs
are merged on GitHub — so the local branch stays wherever it was. Merging it does
nothing and still reports `Already up to date.`, leaving `dev` unsynced while
appearing to succeed.

`--ff-only` is the safety rail: if `dev` has picked up commits of its own, the
merge aborts instead of quietly creating a merge commit. That abort means real
divergence to look at.

---

## Cheat sheet

```bash
# Quality gates
make lint                  # ruff + eslint + prettier
make test                  # pytest
make check                 # both
make fmt                   # apply fixes
make docker-smoke          # build the image and prove it serves

# OpenSpec
openspec list
openspec validate <change> --strict
/opsx:propose <name-or-description>
/opsx:apply   <change>
/ship

# Branch → image tag
#   dev   → bozodev/glimpse-media-viewer:dev                (test)
#   main  → bozodev/glimpse-media-viewer:latest             (production)
#   main + new VERSION → also :<VERSION> + tag + Release

# Cut a release (after validating on :dev)
git checkout dev && git pull
echo "2.0.0" > VERSION && git commit -am "Release 2.0.0" && git push
#   then merge dev → main via PR, and resync:
git checkout dev && git fetch origin && git merge --ff-only origin/main && git push
```

### Repo layout

```
Glimpse/
├─ CLAUDE.md              # always-loaded project rules for Claude Code
├─ VERSION                # drives the pinned image tag, git tag, and Release
├─ docker-compose.yml     # FROZEN — every user has a copy
├─ Dockerfile
├─ Makefile               # the quality gates
├─ config/                # entrypoint.sh, nginx.conf, supervisord.conf
├─ scripts/               # glimpse_config.py + the Plex / Jellyfin+Emby fetchers
├─ web/                   # the static frontend served by nginx
├─ tests/                 # pytest
├─ data/                  # the snapshot (mounted volume; git-ignored)
├─ docs/                  # this file + docker.md
├─ openspec/              # config.yaml, specs/, changes/
└─ .claude/commands/      # /ship and the /opsx:* slash commands
```
