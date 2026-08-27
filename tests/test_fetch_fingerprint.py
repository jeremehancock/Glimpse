"""What decides whether a restart re-imports a server, and what it may disclose.

A container restart used to re-import every configured library unconditionally.
Because supervisord starts last, the container refused connections on 9090 for
the whole of it — so rebuilding to change nothing at all cost a full re-import of
data already sitting on the volume.

Each server now records a fingerprint of the settings that produced its last
**successful** import. On boot the entrypoint compares; a match skips that
server's fetch. Three properties make that safe, and each is pinned below.

**The input set is exact, in both directions.** Only a server's URL, token and
exclusion list change what a snapshot contains. `APP_TITLE`, `TZ`,
`PRIMARY_SERVER`, `SORT_BY_DATE_ADDED` and `CRON_SCHEDULE` change how it is
displayed or when it is refreshed — re-importing a library because someone
renamed the app would be a regression, not a safeguard. This is asserted the way
`test_compose_surface.py` asserts the compose surface: a new field on `Server`
fails here until someone decides on purpose whether it belongs, because the
failure mode of guessing is silent in both directions.

**A hash, never the values.** `/app/data` is served by nginx and this app has no
authentication, so a file holding the token would be a credential download for
anyone who can reach the port.

**Stringified, never joined.** A URL and a library name both admit commas, so
joined text collides — `'a,b'` with `'c'` and `'a'` with `'b,c'` are the same
string. A collision here is a fingerprint that *matches when the settings
differ*, which silently withholds the user's change until a scheduled run
happens to fire. That is the one direction this must never be wrong in: a false
"changed" costs one unnecessary import, a false "unchanged" costs the user their
setting.
"""

import dataclasses

import pytest

from glimpse_config import Server, resolve, write_fingerprints

# Exactly the fields that determine what a snapshot CONTAINS, in the order
# `fetch_inputs()` reports them. Both directions are asserted: a field added to
# Server that belongs here must be added here, and one that does not belong must
# be shown not to matter.
FINGERPRINTED_FIELDS = ('url', 'token', 'exclude_libraries')

# Everything else on Server. Present so that adding a field forces a choice
# rather than defaulting into one.
UNFINGERPRINTED_FIELDS = ('id', 'name')


def server(**overrides) -> Server:
    base = {
        'id': 'plex',
        'name': 'Plex',
        'url': 'http://plex.local:32400',
        'token': 'a-real-looking-token',
        'exclude_libraries': '',
    }
    return Server(**{**base, **overrides})


def test_the_fingerprinted_field_set_is_exact():
    """Adding a field to Server must fail here until someone decides about it."""
    declared = tuple(f.name for f in dataclasses.fields(Server))
    assert set(declared) == set(FINGERPRINTED_FIELDS) | set(UNFINGERPRINTED_FIELDS), (
        'Server gained or lost a field. Decide whether it changes what a '
        'snapshot CONTAINS: if it does it belongs in fetch_inputs(), and if it '
        'does not, add it to UNFINGERPRINTED_FIELDS to say so on purpose. '
        'Do not relax this assertion — a field that silently skips the '
        'fingerprint means a settings change that silently never takes effect.'
    )


@pytest.mark.parametrize('field', FINGERPRINTED_FIELDS)
def test_every_fingerprinted_field_changes_the_hash(field):
    before = server().fingerprint()
    after = server(**{field: 'something-else-entirely'}).fingerprint()
    assert before != after, f'{field} does not affect the fingerprint'


@pytest.mark.parametrize('field', UNFINGERPRINTED_FIELDS)
def test_no_other_field_changes_the_hash(field):
    """Identity is not content. Two servers with the same credentials and
    exclusions hold the same library whatever they are called."""
    before = server().fingerprint()
    after = server(**{field: 'renamed'}).fingerprint()
    assert before == after, (
        f'{field} affects the fingerprint. It does not change what the snapshot '
        'contains, so it would force re-imports that achieve nothing.'
    )


def test_identical_settings_produce_an_identical_fingerprint():
    """Without this the skip never fires and the whole change does nothing."""
    assert server().fingerprint() == server().fingerprint()


@pytest.mark.parametrize(
    'variant',
    [
        'Comedy,Action',  # reordered
        ' Action , Comedy ',  # re-spaced
        'Action,,Comedy',  # empty entry
        ',Action,Comedy,',  # leading and trailing separators
        'Comedy,Action,Comedy',  # repeated
    ],
)
def test_an_exclusion_list_is_compared_by_effect_not_by_spelling(variant):
    """All of these exclude the same libraries, so none may cost a re-import."""
    canonical = server(exclude_libraries='Action,Comedy').fingerprint()
    assert server(exclude_libraries=variant).fingerprint() == canonical


def test_a_changed_exclusion_list_still_changes_the_fingerprint():
    """The normalisation above must not flatten a real difference.

    Exclusions are in the fingerprint precisely so that editing them and
    restarting applies them, rather than waiting for the next scheduled run.
    """
    before = server(exclude_libraries='Action,Comedy').fingerprint()
    after = server(exclude_libraries='Action').fingerprint()
    assert before != after


def test_the_encoding_does_not_collide_across_field_boundaries():
    """The reason this is `json.dumps` of a list and not a delimiter join."""
    left = server(url='a,b', token='c').fingerprint()
    right = server(url='a', token='b,c').fingerprint()
    assert left != right, (
        'Two different settings hash the same. A joined string cannot tell '
        'where one field ends and the next begins when the fields themselves '
        'contain the separator — and the resulting failure is a restart that '
        'skips an import the user asked for.'
    )


def test_a_fingerprint_discloses_none_of_its_inputs():
    """It is written into a directory nginx serves, on an app with no login."""
    secret_url = 'http://plex.internal.example:32400'
    secret_token = 'sk-do-not-leak-me'
    fingerprint = server(
        url=secret_url, token=secret_token, exclude_libraries='Private Films'
    ).fingerprint()

    for secret in (secret_url, secret_token, 'Private Films', 'plex.internal'):
        assert secret not in fingerprint, f'{secret!r} is recoverable from the fingerprint'

    assert len(fingerprint) == 64 and set(fingerprint) <= set('0123456789abcdef')


# --- what gets written to disk --------------------------------------------


def test_one_file_is_written_per_configured_server(tmp_path):
    resolved = resolve(
        {
            'PLEX_URL': 'http://plex:32400',
            'PLEX_TOKEN': 'plex-token',
            'JELLYFIN_URL': 'http://jellyfin:8096',
            'JELLYFIN_TOKEN': 'jellyfin-token',
        }
    )
    write_fingerprints(resolved, tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ['jellyfin', 'plex']


def test_nothing_is_written_for_an_unconfigured_server(tmp_path):
    """Emby has no credentials here, so it has no fetch and no fingerprint."""
    resolved = resolve({'PLEX_URL': 'http://plex:32400', 'PLEX_TOKEN': 'plex-token'})
    write_fingerprints(resolved, tmp_path)

    assert not (tmp_path / 'emby').exists()


def test_a_written_file_holds_the_hash_and_nothing_else(tmp_path):
    """The entrypoint compares these with `cmp`, so any extra byte is a mismatch."""
    resolved = resolve({'PLEX_URL': 'http://plex:32400', 'PLEX_TOKEN': 'plex-token'})
    write_fingerprints(resolved, tmp_path)

    written = (tmp_path / 'plex').read_text(encoding='utf-8')
    assert written == resolved.servers[0].fingerprint()


def test_the_destination_directory_is_created(tmp_path):
    """The entrypoint points this at /run, which is empty on every boot."""
    resolved = resolve({'PLEX_URL': 'http://plex:32400', 'PLEX_TOKEN': 'plex-token'})
    destination = tmp_path / 'glimpse' / 'fingerprints'

    write_fingerprints(resolved, destination)

    assert (destination / 'plex').is_file()
