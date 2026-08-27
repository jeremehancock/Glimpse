# release-publishing Specification

## Purpose
TBD - created by archiving change modernize-ci-action-runtimes. Update Purpose after archive.
## Requirements
### Requirement: No workflow action runs on a deprecated runtime

Every third-party action referenced by a workflow in `.github/workflows/` SHALL
declare a JavaScript runtime that GitHub still ships on its hosted runners. An
action declaring a runtime GitHub has deprecated MUST be upgraded to a release
that declares a current one, or replaced.

The failure mode is what makes this a requirement rather than housekeeping.
GitHub retires a runtime in two steps: first the deprecated action is *forced*
onto the newer runtime and prints a warning, and only later does it stop running.
During the first step nothing is broken, so there is nothing to notice except a
line in a log that is already noisy — and the release pipeline is the one path a
build reaches a user through. The window between the warning and the failure is
the entire opportunity to act, and it closes on a runner-image rollout this
project neither controls nor is notified of.

The warning is emitted per run, not per repository, so the CI log and the
publish log both carry it. Treat it as a build failure that has not happened yet.

#### Scenario: An action declares a deprecated runtime

- **WHEN** a workflow references an action whose `action.yml` declares a Node
  runtime GitHub has announced the deprecation of
- **THEN** that reference SHALL be updated to a release of the same action
  declaring a runtime GitHub currently supports
- **AND** the update SHALL be made across every workflow file that references
  that action, not only the one whose log surfaced the warning

#### Scenario: A workflow runs with no runtime deprecation warning

- **WHEN** CI or the publish workflow completes on a GitHub-hosted runner
- **THEN** no step SHALL report that its action is being forced onto a newer
  Node runtime

### Requirement: The action version set is pinned and asserted exactly

The version of every action the workflows use SHALL be asserted by
`make test` against an explicit table, in **both** directions: an action present
in a workflow but absent from the table fails, and a table entry naming a version
a workflow does not use fails.

Both directions are load-bearing, and the second is the one that is easy to
argue away. A workflow file is edited rarely and read less often, so an action
version drifts by *nothing happening to it*. A one-directional check tells you
about a downgrade someone typed; the exact assertion tells you about the version
nobody has looked at since it was written, which is the one that reaches
end-of-life. This mirrors `tests/test_compose_surface.py`, which asserts the
compose variable list exactly for the same reason.

An intentional bump is expected to fail this test. That is the review step, not
an obstacle to it: the fix is to move the table in the same commit as the
workflow edit, never to relax the assertion.

The test SHALL pin versions it can read from the repository. It SHALL NOT reach
the network to ask whether a newer release exists, and it SHALL NOT claim to
prove that the pinned versions are still current — a pinned table is a record of
a reviewed decision, not a freshness check. Nothing in the gate can detect a
deprecation announced after the table was written.

#### Scenario: A workflow references an action the table does not name

- **WHEN** a workflow step is added or edited to reference an action version not
  present in the pinned table
- **THEN** `make test` SHALL fail and name the action and the version found

#### Scenario: The table names a version no workflow uses

- **WHEN** the pinned table names an action version that no workflow file
  references
- **THEN** `make test` SHALL fail, rather than passing on the strength of the
  references that do match

#### Scenario: A deliberate upgrade

- **WHEN** an action is upgraded on purpose
- **THEN** the pinned table SHALL be updated in the same commit as the workflow
  file
- **AND** the assertion SHALL NOT be weakened, scoped down, or skipped to
  accommodate the change

### Requirement: The toolchain Node version is distinct from the runner's

`ci.yml` selects a Node version for ESLint and Prettier via `actions/setup-node`.
That version SHALL be understood as the toolchain's Node, not the runner's, and
SHALL be a Node release still under support.

These are two different things that both read as "the Node version in CI", and
conflating them sends the next person to the wrong line. The runtime an action
runs on is chosen by GitHub from the action's own `action.yml`; `setup-node`
cannot influence it, and bumping `node-version` does not silence a runtime
deprecation warning. Conversely, upgrading the actions does not move the version
ESLint and Prettier run on.

Nothing in `web/` is built or bundled and no Node runs in the published image, so
this version affects only whether the lint gate is running on a supported
interpreter. `docs/development-workflow.md` states a **floor** for local
development; CI selecting a higher version is consistent with that floor and is
not a change to it.

#### Scenario: The lint toolchain runs on a supported Node

- **WHEN** CI installs Node to run `make lint`
- **THEN** the selected version SHALL be a Node release still receiving support

#### Scenario: A runtime deprecation warning is reported

- **WHEN** a workflow run warns that an action is being forced onto a newer Node
  runtime
- **THEN** the fix SHALL be to upgrade the action, and changing `node-version`
  SHALL NOT be treated as addressing it

### Requirement: An action upgrade does not alter what is published

An upgrade undertaken to change an action's runtime SHALL NOT change any
workflow's triggers, job conditions, permissions, computed tags, or published
artifacts. Where the newer action changes behavior, that difference MUST be
stated and shown to be inert, or handled as its own change.

A version bump is the cheapest-looking edit in the repository and the one with
the least local evidence of what it did: the diff is one character, and the
behavior lives in someone else's release notes. Bundling a behavior change into
it means the pipeline that publishes to every existing install changed in a way
the diff does not show.

#### Scenario: The publish path is unchanged

- **WHEN** the action versions have been upgraded
- **THEN** the same commits SHALL publish the same image tags to the same image
  name, by the same triggers, as before the upgrade

#### Scenario: A newer action major changes behavior

- **WHEN** the chosen version of an action introduces a behavior change relative
  to the version replaced
- **THEN** that change SHALL be identified before the upgrade is made
- **AND** SHALL be recorded together with why it cannot affect this repository,
  or else carried out as a separate, specified change

