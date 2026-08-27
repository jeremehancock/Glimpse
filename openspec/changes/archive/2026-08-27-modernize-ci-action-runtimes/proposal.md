## Why

Every push to this repo now prints a deprecation warning, and every publish run
carries it in the build log. GitHub has stopped shipping Node 20 on its runners:
actions that declare `node20` are silently force-run on Node 24 today and will
stop running at all when that fallback is withdrawn. The pipeline that publishes
`bozodev/glimpse-media-viewer` is the only path a release reaches a user
through — it must not be the thing that breaks on a runner-image rollout the
project does not control.

## What Changes

- Bump every GitHub Action in `.github/workflows/` to its current major, so no
  action declares a `node20` runtime. Nine distinct actions, 11 `uses:` lines,
  across two files.
- **Fix all nine, not the six the warning named.** The reported warning came from
  the `Build and push` job only. `ci.yml` has three more actions on `node20` in
  a log nobody read, and `softprops/action-gh-release@v2` is in the *same* job as
  the six but sits behind `if: steps.ver.outputs.release == 'true'` — a step that
  does not run emits no warning about its runtime. That one would surface for the
  first time at a release, after the image had already been pushed.
- Bump the toolchain Node in `ci.yml` from `20` to `24`, so the Node that runs
  ESLint and Prettier matches the runtime the actions themselves now use. This
  is separate from the deprecation — it is the version `make lint` runs on, not
  the version the runner supplies to actions.
- Add `tests/test_workflow_actions.py`, pinning the expected version of every
  action the workflows use, in both directions — the same shape as
  `tests/test_compose_surface.py`. An unreviewed bump fails the gate just as a
  silent downgrade does.
- **Not breaking.** No workflow trigger, job condition, tag expression, or
  published artifact changes. The same commits publish the same tags to the same
  image name.

The **frozen `docker-compose.yml` surface is untouched**. This change edits no
file a user has a copy of, reads no new environment variable, and does not alter
what the built image contains — an existing user's compose file is not merely
compatible, it is unaffected.

One behavior change is worth naming even though it is inert here:
`actions/checkout@v7` refuses to check out a *fork* pull-request ref under
`workflow_run`. `docker-publish.yml` uses `workflow_run`, but already declines to
run on forks via its `github.repository_owner == 'jeremehancock'` guard, and CI
is push-only so no fork PR reaches it. The new refusal has nothing to refuse.

## Capabilities

### New Capabilities

- `release-publishing`: already named in the capability map in
  `openspec/config.yaml` but never given a spec file. This change writes the
  first one, scoped to what it actually decides — how the pipeline's third-party
  actions are versioned and what the gate checks about them. The rest of the
  capability (branch-to-tag mapping, the VERSION-driven release detection)
  remains as it is: implemented and unspecced, to be filled in by the change
  that next touches it. A partial spec is not an invitation to write the missing
  parts from the code.

### Modified Capabilities

None. No app behavior changes.

## Impact

| Affected | How |
| --- | --- |
| `.github/workflows/ci.yml` | 4 `uses:` bumps (checkout twice), 1 `node-version` bump |
| `.github/workflows/docker-publish.yml` | 7 `uses:` bumps |
| `tests/test_workflow_actions.py` | New — pins the version table |
| `openspec/specs/release-publishing/spec.md` | New — first spec for a mapped capability |
| The published image | Nothing. Same base image, same Dockerfile, same tags |
| `docker-compose.yml` | Untouched |
| Local dev | Nothing. `make lint` / `make test` / `make docker-smoke` unchanged; `docs/development-workflow.md` states Node **18+** as a floor, which 24 satisfies |

Runner requirement: `actions/checkout@v5+` needs runner `v2.327.1` or newer.
`ubuntu-latest` on GitHub-hosted runners is well past that; this repo uses no
self-hosted runners.
