"""The workflows' third-party actions, pinned to an exact table.

GitHub retires a JavaScript runtime in two steps: first an action declaring the
old one is *forced* onto the new one and prints a warning, and only later does it
stop running at all. During the first step nothing is broken, so there is nothing
to notice except a line in a build log that is already noisy. That window is the
entire opportunity to act, and it closes on a runner-image rollout this project
neither controls nor is notified of — on the one path a release reaches a user
through.

A workflow file is edited rarely and read less often, so an action version drifts
by *nothing happening to it*. That is why the assertion below runs in both
directions. A one-directional check tells you about a downgrade someone typed;
the exact match tells you about the version nobody has looked at since it was
written, which is the one that reaches end-of-life. Same reasoning, and the same
shape, as `test_compose_surface.py`.

WHAT THIS TEST CANNOT DO, so nobody trusts it further than it goes:

  * It does not know whether a pinned version is still current. That needs the
    network, and a gate that needs the network fails on GitHub's bad days rather
    than on this repo's. Deprecation notices arrive in a build log; they will not
    arrive here.
  * It does not read each action's `action.yml`, so it cannot assert that no
    action declares a deprecated runtime. It asserts only that the versions in
    the workflows are the versions someone reviewed.

An intentional bump is EXPECTED to fail this test. That is the review step, not
an obstacle to it: move the table in the same commit as the workflow edit. Never
relax, scope down, or skip the assertion to accommodate a change.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip('yaml')

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / '.github' / 'workflows'

# Every action the workflows use, at the version it is pinned to. All of these
# declared `node20` before 2026-08-27 and were bumped together; the versions here
# declare `node24`. Read from each action's own `action.yml` at the tag — not
# inferred from release notes, which describe what changed rather than what the
# runtime is.
PINNED_ACTIONS = {
    'actions/checkout': 'v7',
    'actions/setup-python': 'v7',
    'actions/setup-node': 'v7',
    'docker/setup-qemu-action': 'v4',
    'docker/setup-buildx-action': 'v4',
    'docker/login-action': 'v4',
    'docker/metadata-action': 'v6',
    'docker/build-push-action': 'v7',
    'softprops/action-gh-release': 'v3',
}


def workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob('*.yml')) + sorted(WORKFLOWS_DIR.glob('*.yaml'))


def used_actions() -> dict[str, set[str]]:
    """Every `uses:` in every workflow, as action -> set of versions referenced.

    Parsed, never regexed. A regex over `uses:` lines reads a commented-out step
    as live and misses one written in flow style, and it fails in the direction
    that matters: the test keeps passing while the table no longer describes the
    file.

    A set of versions per action, not a single version, so that the same action
    pinned to two different versions across files is a failure rather than
    whichever one happened to be read last.
    """
    found: dict[str, set[str]] = {}
    for path in workflow_files():
        workflow = yaml.safe_load(path.read_text())
        for job in (workflow.get('jobs') or {}).values():
            for step in job.get('steps') or []:
                ref = step.get('uses')
                if not ref:
                    continue  # a `run:` step
                name, _, version = ref.partition('@')
                found.setdefault(name, set()).add(version)
    return found


def test_workflows_are_parseable():
    """Guards the test itself: an empty parse would make every assertion vacuous."""
    files = workflow_files()
    assert files, f'no workflow files under {WORKFLOWS_DIR}'
    assert used_actions(), 'parsed the workflows but found no `uses:` steps at all'


def test_every_action_used_is_pinned():
    unpinned = sorted(set(used_actions()) - set(PINNED_ACTIONS))
    assert not unpinned, (
        f'workflow steps use actions the pinned table does not name: {unpinned}. '
        'Add them to PINNED_ACTIONS in the same commit, having checked the '
        "runtime each one declares in its own action.yml — don't skip the table."
    )


def test_table_names_no_unused_action():
    """The direction that is easy to argue away, and the one that catches rot.

    A table entry no workflow references is a version nobody is reviewing. Left
    in, it makes the table look maintained while describing nothing.
    """
    unused = sorted(set(PINNED_ACTIONS) - set(used_actions()))
    assert not unused, (
        f'PINNED_ACTIONS names actions no workflow uses: {unused}. '
        'Remove them, rather than leaving the table describing a version that '
        'is no longer in the pipeline.'
    )


def test_pinned_versions_match():
    found = used_actions()
    mismatched = {
        name: sorted(versions)
        for name, versions in sorted(found.items())
        if name in PINNED_ACTIONS and versions != {PINNED_ACTIONS[name]}
    }
    assert not mismatched, '\n'.join(
        [
            'workflow action versions do not match the pinned table:',
            *(
                f'  {name}: workflows use {versions}, table pins {PINNED_ACTIONS[name]!r}'
                for name, versions in mismatched.items()
            ),
            '',
            'If this bump is deliberate, move the table in this same commit.',
        ]
    )
