"""How the library snapshot reaches disk, and what may never happen to it there.

nginx serves `/app/data` to a frontend that can load at any instant, including
every instant of a fetch run. So a writer here has to be correct not only when
it finishes but at every moment in between, and for years it was not:

**The snapshot was deleted at the START of every run.** Both fetchers opened
`fetch_and_save_data()` with `clean_existing_data()`, which unlinked
`movies.json` and `tvshows.json`, and wrote the replacements last. For the
minutes between — an import, on a real library — the page shell loaded fine and
the snapshot 404'd, so the viewer was told `Failed to load movie data. Please
try again later.` Not a site that was down; a site that was broken, which is
harder to recognise and much harder to diagnose.

**So a failed run destroyed the library.** Both fetchers give up early on a
number of conditions, and every one of those paths ran *after* the delete. A
media server that happened to be restarting when cron fired left the viewer with
an empty library until a later run succeeded — and an empty library is
indistinguishable from a correctly configured server holding no media, which is
the ambiguity this project refuses everywhere else.

The fix is one rule: **never modify a published file.** Write a complete copy
beside it and rename it over the top. What is pinned below is that rule's
structure — that neither fetcher deletes or truncates a snapshot, and that the
shared publisher in `scripts/snapshot_io.py` behaves the way the rule needs.

The permissions assertion deserves its own note. A rename carries the temp
file's mode and owner with it, so a publisher that sets the mode *after* the
rename produces a flawless atomic swap that nginx then answers **403** to — a
fresh way to break the site, reached while fixing the old one, and invisible to
every check here that does not look at the mode. `make test` has no web server;
this assertion is what stands in for one.
"""

import json
import os
import re
import stat
from pathlib import Path

import pytest

import snapshot_io

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / 'scripts'

# Both fetchers, always. Emby and Jellyfin are one adapter with two identities,
# so this is two files covering three servers — and a fix applied to one and not
# the other is a bug this project has already shipped.
FETCHERS = ('plex_data_fetcher.py', 'jellyfin_data_fetcher.py')

SNAPSHOT_NAMES = ('movies.json', 'tvshows.json')


@pytest.fixture(params=FETCHERS)
def fetcher_source(request) -> str:
    path = SCRIPTS / request.param
    assert path.is_file(), f'{request.param} is gone — this test is now checking nothing'
    return path.read_text(encoding='utf-8')


def test_no_fetcher_deletes_the_snapshot_it_is_replacing(fetcher_source):
    """The defect itself: `clean_existing_data()` and anything shaped like it."""
    assert 'clean_existing_data' not in fetcher_source, (
        'A fetcher deletes the snapshot before rebuilding it. That leaves the '
        'site reporting a load failure for the whole import, and leaves the '
        'library deleted outright if the run then fails.'
    )
    assert not re.search(r'\.unlink\(', fetcher_source), (
        'A fetcher unlinks a file. Publishing is a rename over the top; nothing '
        'in a fetch run should need to remove anything.'
    )


def test_no_fetcher_writes_a_snapshot_in_place(fetcher_source):
    """A truncating open on a served path has a window even on the happy path."""
    for name in SNAPSHOT_NAMES:
        stem = name.removesuffix('.json')
        # e.g. `open(movies_file, 'w')` — the original write.
        assert not re.search(rf"open\(\s*{stem}_file\s*,\s*['\"]w", fetcher_source), (
            f'{name} is written through a truncating open. Publish it through '
            'snapshot_io.publish_json so a reader never sees a partial file.'
        )
    assert 'snapshot_io' in fetcher_source, (
        'A fetcher no longer routes its snapshot through the shared publisher. '
        'Two hand-rolled copies of this are what the shared module prevents.'
    )


def test_a_fetcher_reports_failure_through_its_exit_status(fetcher_source):
    """Without this, "record the fingerprint only on success" cannot be built.

    `main()` used to ignore what `fetch_and_save_data()` returned, so the
    process exited 0 whether the fetch worked or not — and the entrypoint's
    "initial fetch failed" warning had therefore never once run.
    """
    exits_on_failure = re.search(
        r'if not fetcher\.fetch_and_save_data\(\):\s*\n\s*sys\.exit\(1\)', fetcher_source
    )
    assert exits_on_failure, (
        'main() does not exit non-zero on a failed fetch. The entrypoint reads '
        'that exit code to decide whether to record a settings fingerprint; '
        'without it, a failed fetch is recorded as a successful import.'
    )


# --- the publisher itself -------------------------------------------------


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    (tmp_path / 'movies.json').write_text('["previous movies"]', encoding='utf-8')
    (tmp_path / 'tvshows.json').write_text('["previous tv"]', encoding='utf-8')
    return tmp_path


def _targets(directory: Path) -> tuple[Path, Path]:
    return directory / 'movies.json', directory / 'tvshows.json'


def test_publishing_replaces_both_targets(snapshot_dir):
    movies, tvshows = _targets(snapshot_dir)
    snapshot_io.publish_json([(movies, ['a']), (tvshows, ['b'])])

    assert json.loads(movies.read_text()) == ['a']
    assert json.loads(tvshows.read_text()) == ['b']


@pytest.fixture
def hostile_umask():
    """A umask under which the mode must be SET rather than inherited.

    This fixture is the entire test. Without it the assertion below passes on a
    publisher that never touches the mode at all: the usual umask of 022 already
    turns a fresh file into 0644, so the right answer arrives by coincidence and
    the check proves nothing. Verified — deleting the `chmod` from
    `snapshot_io` left this test green until the umask was forced.

    That is not a hypothetical container. A restrictive umask is exactly the
    environment where an inherited mode goes wrong, so it is the one worth
    testing under.
    """
    previous = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(previous)


def test_a_published_file_is_readable_by_nginx(snapshot_dir, hostile_umask):
    """0644, set on the temp — a rename carries the mode it had as a temp."""
    movies, _ = _targets(snapshot_dir)
    snapshot_io.publish_json([(movies, ['a'])])

    mode = stat.S_IMODE(movies.stat().st_mode)
    assert mode == 0o644, (
        f'Published at {mode:#o}. nginx runs as www-data and answers 403 to a '
        'file it cannot read, which looks nothing like a permissions bug from '
        'the browser. The mode has to be set explicitly, on the temp file, '
        'because a rename carries the mode the temp had.'
    )


def test_a_failure_publishes_nothing_and_leaves_the_previous_snapshot(snapshot_dir):
    """The whole point: a run that gives up has not touched what is being served."""
    movies, tvshows = _targets(snapshot_dir)

    class Unserialisable:
        pass

    with pytest.raises(TypeError):
        snapshot_io.publish_json([(movies, ['new']), (tvshows, Unserialisable())])

    assert json.loads(movies.read_text()) == ['previous movies'], (
        'movies.json was published while its partner failed. Neither may be '
        'published until both are written: they are read as a pair by one page '
        'load, so publishing one early shows the viewer two points in time.'
    )
    assert json.loads(tvshows.read_text()) == ['previous tv']


def test_a_failure_leaves_no_temp_file_behind(snapshot_dir):
    """A partial temp in a directory nginx serves is litter with a URL.

    Note which one this catches: the temp belonging to the payload that FAILED.
    An implementation that registers each temp for cleanup after writing it
    cleans up every temp except that one — the only one that exists in a
    half-written state.
    """
    movies, tvshows = _targets(snapshot_dir)

    class Unserialisable:
        pass

    with pytest.raises(TypeError):
        snapshot_io.publish_json([(movies, ['new']), (tvshows, Unserialisable())])

    leftovers = sorted(p.name for p in snapshot_dir.iterdir() if p.name.endswith('.tmp'))
    assert leftovers == [], f'temp files survived a failed publish: {leftovers}'


def test_the_temp_file_is_beside_its_target(tmp_path):
    """Same directory, or `Path.replace()` stops being atomic.

    `/app/data` is a mounted volume. Staging through `/tmp` would put the temp
    on a different filesystem, turning the rename into a copy — non-atomic, and
    the only property this module exists to provide is gone. Silently: it would
    still produce the right bytes.
    """
    target = tmp_path / 'nested' / 'movies.json'
    assert snapshot_io.temp_path_for(target).parent == target.parent


def test_the_temp_name_is_fixed_not_random(tmp_path):
    """A killed run leaves its temp behind; a fixed name means one, not a pile."""
    target = tmp_path / 'movies.json'
    assert snapshot_io.temp_path_for(target) == snapshot_io.temp_path_for(target)


def test_prepare_is_applied_to_the_temp_not_the_target(snapshot_dir):
    """Ownership has to be set before the rename, for the same reason as the mode."""
    movies, _ = _targets(snapshot_dir)
    seen: list[Path] = []

    snapshot_io.publish_json([(movies, ['a'])], prepare=seen.append)

    assert seen == [snapshot_io.temp_path_for(movies)], (
        'prepare() ran against the published path. Applied after the rename it '
        'is applied too late — the file has already been served-visible with '
        "the temp's ownership."
    )


def test_publishing_creates_a_missing_directory(tmp_path):
    """A first run has no previous snapshot to preserve and must still work."""
    target = tmp_path / 'brand-new' / 'movies.json'
    snapshot_io.publish_json([(target, ['a'])])
    assert json.loads(target.read_text()) == ['a']
