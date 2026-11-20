"""The Jellyfin/Emby fetcher is one adapter with two identities.

Where the two servers differ, the identity decides. Two differences exist today,
and both were bugs before the identity existed:

- **Sign-in.** Current Jellyfin answers the legacy `X-Emby-Token` header with a
  401. The fetch fails, the previous snapshot keeps being served, and the
  library silently stops updating with a valid key. Jellyfin is sent
  `Authorization: MediaBrowser Token="..."`; Emby keeps `X-Emby-Token`.
- **Exclusions.** The fetcher read `EMBY_EXCLUDE_LIBRARIES or
  JELLYFIN_EXCLUDE_LIBRARIES` whichever server it was fetching, so a container
  configured with both applied Emby's exclusions to Jellyfin's boot fetch.

These check the session the fetcher builds, which is what every request goes
through. That the Jellyfin header is the one a real Jellyfin accepts was checked
against a running server, which `make test` has no way to do.
"""

import pytest

pytest.importorskip('requests')

import jellyfin_data_fetcher as fetcher_module
from jellyfin_data_fetcher import (
    JellyfinDataFetcher,
    excluded_libraries_from_env,
)

TOKEN = 'abc123'


def build(tmp_path, **kwargs):
    return JellyfinDataFetcher('http://media.example:8096/', TOKEN, tmp_path / 'out', **kwargs)


def test_jellyfin_signs_in_with_the_authorization_header(tmp_path):
    headers = build(tmp_path, server='jellyfin').session.headers
    assert headers['Authorization'] == f'MediaBrowser Token="{TOKEN}"'


def test_jellyfin_is_not_sent_the_legacy_header(tmp_path):
    """Sending both is not a safe hedge: it is not ours to rely on how a server
    treats a header it has stopped honouring."""
    assert 'X-Emby-Token' not in build(tmp_path, server='jellyfin').session.headers


def test_emby_signs_in_as_it_always_has(tmp_path):
    headers = build(tmp_path, server='emby').session.headers
    assert headers['X-Emby-Token'] == TOKEN
    assert 'Authorization' not in headers


def test_an_unnamed_identity_is_jellyfin(tmp_path):
    """A hand-run command written before `--server` existed keeps working."""
    headers = build(tmp_path).session.headers
    assert headers['Authorization'] == f'MediaBrowser Token="{TOKEN}"'


def test_the_command_line_defaults_to_jellyfin(monkeypatch):
    seen = {}

    class Recorder:
        def __init__(self, *args, server, **kwargs):
            seen['server'] = server

        def fetch_and_save_data(self):
            return True

    monkeypatch.setattr(fetcher_module, 'JellyfinDataFetcher', Recorder)
    monkeypatch.setattr('sys.argv', ['fetcher', '--url', 'http://x', '--token', 't'])
    fetcher_module.main()
    assert seen['server'] == 'jellyfin'


BOTH = {'JELLYFIN_EXCLUDE_LIBRARIES': 'Home Videos', 'EMBY_EXCLUDE_LIBRARIES': 'Private'}


def test_jellyfin_reads_only_its_own_exclusions():
    assert excluded_libraries_from_env('jellyfin', BOTH) == ['Home Videos']


def test_emby_reads_only_its_own_exclusions():
    assert excluded_libraries_from_env('emby', BOTH) == ['Private']


def test_the_other_identity_s_list_alone_excludes_nothing():
    assert excluded_libraries_from_env('jellyfin', {'EMBY_EXCLUDE_LIBRARIES': 'Private'}) == []


def test_the_exclusion_list_is_parsed_as_before():
    env = {'JELLYFIN_EXCLUDE_LIBRARIES': ' Home Videos , 4,, '}
    assert excluded_libraries_from_env('jellyfin', env) == ['Home Videos', '4']


@pytest.mark.parametrize('server', ['jellyfin', 'emby'])
def test_the_command_line_applies_the_identity_s_exclusions(monkeypatch, server):
    seen = {}

    class Recorder:
        def __init__(self, url, token, output, page_size, excluded, server):
            seen['excluded'] = excluded

        def fetch_and_save_data(self):
            return True

    for key, value in BOTH.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(fetcher_module, 'JellyfinDataFetcher', Recorder)
    monkeypatch.setattr(
        'sys.argv', ['fetcher', '--server', server, '--url', 'http://x', '--token', 't']
    )
    fetcher_module.main()
    assert seen['excluded'] == excluded_libraries_from_env(server, BOTH)
