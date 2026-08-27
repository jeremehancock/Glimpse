## Context

Two workflow files reference nine distinct third-party actions, and **all nine
declare `node20`**. The reported warning names only six, because it came from the
`Build and push` job alone. The other three are hidden by two different
mechanisms, and both are worth naming — a fix scoped to the warning text is a
fix that leaves the deprecation in place:

- `actions/setup-python@v5` and `actions/setup-node@v4` live in `ci.yml`, a
  separate workflow with its own log. They warn too; that log was not the one
  read.
- `softprops/action-gh-release@v2` is in the same job as the six, but its step is
  conditional — `if: steps.ver.outputs.release == 'true'` — and a step that does
  not execute emits no warning about its runtime. It is the same defect, invisible
  in the same log. Left alone, the next release builds and pushes the image and
  *then* fails at the tag step.

**Read the runtime, do not read the warning.** The warning enumerates what ran.

The runtime each action declares was read from its `action.yml` at each candidate
tag, not inferred from release notes:

| Action | In repo | Runtime | Target | Runtime |
| --- | --- | --- | --- | --- |
| `actions/checkout` | v4 | node20 | **v7** | node24 |
| `actions/setup-python` | v5 | node20 | **v7** | node24 |
| `actions/setup-node` | v4 | node20 | **v7** | node24 |
| `docker/setup-qemu-action` | v3 | node20 | **v4** | node24 |
| `docker/setup-buildx-action` | v3 | node20 | **v4** | node24 |
| `docker/login-action` | v3 | node20 | **v4** | node24 |
| `docker/metadata-action` | v5 | node20 | **v6** | node24 |
| `docker/build-push-action` | v6 | node20 | **v7** | node24 |
| `softprops/action-gh-release` | v2 | node20 | **v3** | node24 |

`actions/checkout@v4` appears twice in `ci.yml` and once in `docker-publish.yml`
— three lines for one row above.

Constraints inherited from `CLAUDE.md`: `docker-compose.yml` is frozen (untouched
here — no file a user holds is edited); `make lint` and `make test` are the gate;
CI builds the image only *after* a push, so anything touching `Dockerfile` or
`config/` needs `make docker-smoke` first. This change touches neither, so
`docker-smoke` is not a gate for it — but the publish workflow is not exercised
by any local command at all, which shapes the verification plan below.

## Goals / Non-Goals

**Goals:**

- No action in either workflow declares a deprecated Node runtime.
- The publish path behaves identically: same triggers, same conditions, same
  tags, same image name.
- The version set is asserted by `make test`, exactly, in both directions.
- The one real behavior change in the newer majors is identified and shown inert.

**Non-Goals:**

- Writing the rest of the `release-publishing` spec. Branch-to-tag mapping and
  VERSION-driven release detection stay implemented-and-unspecced; this change
  specs only what it decides.
- SHA-pinning the actions (see Decisions).
- A test that checks whether the pinned versions are *still current*. It cannot
  be done without the network, and a test that reaches the network fails when
  GitHub is slow rather than when the repo is wrong.
- Any change to `Dockerfile`, `config/`, or the frontend.

## Decisions

### Bump to the current major, not to the minimum that clears the warning

The minimum node24 major exists for every action (`checkout@v5`,
`setup-python@v6`, `setup-node@v5`, docker actions the same one major up). It
would clear the warning with strictly fewer behavior changes.

Rejected: `checkout@v5` and `setup-python@v6` are each two majors stale already,
so the minimum bump schedules this same task again — and the cost of this task is
not the edit, it is noticing. The warning was noticed here because a human read a
build log. Landing on the current major buys the longest interval before the next
one, and the pinned table makes the *next* review a diff rather than an audit.

Alternatives considered:

- **Minimum node24 major.** Above.
- **SHA-pin every action.** The supply-chain-correct answer, and genuinely
  better against a compromised tag. Rejected for now because it changes the
  review economics of every future bump — a SHA carries no version information,
  so the pinned table becomes the only place a human can read what version is in
  use, and a stale comment beside a SHA is worse than no comment. It is a real
  change worth making on its own terms, with Dependabot to service it, not a rider
  on a deprecation fix.

### `checkout@v7`'s fork refusal is inert, and here is the argument

`actions/checkout@v7` blocks checking out a fork PR ref under `pull_request_target`
and `workflow_run`. `docker-publish.yml` triggers on `workflow_run` and checks out
`github.event.workflow_run.head_sha`, so the refusal is pointed directly at the
one place this repo could be affected.

It cannot fire, for two independent reasons:

1. The job's `if` requires `github.repository_owner == 'jeremehancock'`, so a run
   in a fork does not start.
2. CI (`ci.yml`) is `push`-only and deliberately does not run on `pull_request`.
   The `workflow_run` trigger therefore only ever fires for a push to `main` or
   `dev` in this repository. There is no fork PR run for it to observe.

Either alone is sufficient; both hold. Recorded here rather than in a code comment
because it is a fact about an *absent* interaction — there is no line in the
workflow it would annotate.

### The other majors' breaking changes, checked and dismissed

- `setup-node@v5` added automatic caching when `package.json` has a
  `packageManager` field; `v6` narrowed that to npm only. `ci.yml` passes
  `cache: npm` explicitly and `package.json` has no `packageManager` field, so
  the behavior is what it already was.
- `setup-python@v7` removed the `pip-install` input. Not used; the workflow runs
  `pip install` as its own step.
- `checkout@v6` writes credentials to a separate file. The workflow does no
  authenticated git operation after checkout — the release step uses
  `softprops/action-gh-release` with `GITHUB_TOKEN`, not the git credential
  helper.
- The docker actions' majors are runtime bumps plus dependency updates; no input
  used here changed name or meaning.
- `checkout@v5+` requires runner `v2.327.1`+. GitHub-hosted `ubuntu-latest` is
  far past this and no self-hosted runner exists in this repo.

### Toolchain Node goes to 24, and it is a different thing

`ci.yml`'s `node-version: '20'` feeds `actions/setup-node`, which chooses the
Node that runs ESLint and Prettier. It has no relationship to the runtime GitHub
picks for an action — bumping it would not have removed a single line from the
warning. Moving it to 24 keeps one Node story in the repo and puts the lint gate
on a supported interpreter.

`docs/development-workflow.md` states **Node 18+** for local development. That is
a floor, and 24 satisfies it — so this is not a docs change, and inventing one
would be the "silently stale docs" rule applied backwards. The doc's warning
about Node 16 (where `npm ci` fails in a way that does not look like a version
problem) stays exactly as true.

Risk accepted: ESLint 9 and Prettier 3 both support Node 24, but CI is where that
gets proven. If the lint step breaks on 24, that is a red CI on `dev` before
anything publishes — which is the gate working.

### The test pins a table, and says what it cannot do

`tests/test_workflow_actions.py` parses every file in `.github/workflows/`,
collects each `uses:` reference, and asserts the set equals an expected mapping
of `action -> version`, both directions, the shape `test_compose_surface.py`
already establishes for the compose surface.

Parse with `yaml.safe_load` — `pyyaml` is already a CI dependency and is used by
`test_compose_surface.py`. A regex over `uses:` lines would also work and is
tempting for a nine-line table, but it reads a commented-out `uses:` as live and
misses one written in flow style. The failure is silent in the direction that
matters: the test passes while the table no longer describes the file.

What it cannot do, stated in the test file so nobody trusts it further than it
goes: it does not know whether a pinned version is current. Nothing offline can.
It catches drift and it makes an intentional bump a reviewed edit; it will not
tell you Node 24 has been deprecated. That notice arrives the same way this one
did — in a build log.

Deliberately **not** asserted: that no action declares `node20`. The test would
have to fetch each `action.yml` from GitHub, and a gate that needs the network
fails on GitHub's bad days rather than on the repo's.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| The publish workflow cannot be run locally — a mistake in it surfaces only on a push to `dev` | `dev` publishes `:dev`, which is exactly the branch's purpose. Validate the run in the Actions tab before merging. The change edits only version numbers, so the blast radius is an action that fails to start, not one that publishes something wrong |
| `action-gh-release@v3`'s step is conditional and will not execute on a `dev` push, so the bump goes unexercised until an actual release | Known and accepted — it is untestable short of releasing. It is also the argument for fixing it now: leaving it at `node20` means it stays unexercised *and* deprecated. Verify at the next `/ship`, where the release step runs for the first time |
| ESLint/Prettier misbehave on Node 24 | Caught by `make lint` in CI on `dev` before any merge to `main`. Reverting one line restores 20 |
| The pinned table fails a future intentional bump and someone relaxes the assertion | Spec'd against explicitly, and the test file says so at the point of failure |
| Bumping several majors at once makes attribution harder if CI goes red | The two workflows are independent — a red `quality` job points at the three `ci.yml` actions, a red `publish` job at the six in `docker-publish.yml`. Bisecting within a file is a per-line revert |

## Migration Plan

1. Edit both workflow files and add the test on `dev`.
2. `make lint && make test` locally. `make docker-smoke` is not required: neither
   `Dockerfile` nor `config/` is touched.
3. Push to `dev`. Confirm in the Actions tab that the `quality` and `docker` jobs
   are green **and** that no step reports a forced runtime.
4. Confirm the `Publish Docker image` run that follows it is green and pushed
   `:dev`.
5. The `action-gh-release@v3` step first executes on the merge to `main` that
   carries a VERSION bump. Watch that run.

Rollback: revert the commit. No published artifact, image tag, or user-facing
file is involved, so there is nothing to undo beyond the workflow files.

## Open Questions

None. SHA-pinning and Dependabot are deferred by decision, not by uncertainty.
