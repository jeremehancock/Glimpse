"""Tests for the environment resolution that replaced ~1,700 lines of sed.

The PRIMARY_SERVER resolution table is the highest-traffic conditional in this
project and had no test at all before this change — it was ~70 lines of nested
shell, and every bug in it reached users. Most of what follows is that table,
enumerated.
"""

import json

import pytest

from glimpse_config import (
    DEFAULT_APP_TITLE,
    DEFAULT_CRON_SCHEDULE,
    THEME_COLORS,
    NoServerConfiguredError,
    resolve,
    write_files,
)

PLEX = {'PLEX_URL': 'http://plex:32400', 'PLEX_TOKEN': 'ptok'}
JELLYFIN = {'JELLYFIN_URL': 'http://jf:8096', 'JELLYFIN_TOKEN': 'jtok'}
EMBY = {'EMBY_URL': 'http://emby:8096', 'EMBY_TOKEN': 'etok'}


def env(*servers, **overrides):
    """Build an environment from server credential sets plus overrides."""
    result = {}
    for server in servers:
        result.update(server)
    result.update(overrides)
    return result


# --------------------------------------------------------------------------
# Server detection
# --------------------------------------------------------------------------


def test_detects_only_servers_with_both_url_and_token():
    resolved = resolve(env(PLEX, JELLYFIN))
    assert [s.id for s in resolved.servers] == ['plex', 'jellyfin']


@pytest.mark.parametrize(
    'partial',
    [
        {'EMBY_URL': 'http://emby:8096'},
        {'EMBY_TOKEN': 'etok'},
        {'EMBY_URL': 'http://emby:8096', 'EMBY_TOKEN': ''},
        {'EMBY_URL': '   ', 'EMBY_TOKEN': 'etok'},
    ],
    ids=['url-only', 'token-only', 'empty-token', 'blank-url'],
)
def test_half_configured_server_is_not_configured(partial):
    """A URL without a token cannot be queried; a token without a URL has
    nothing to query. Half-configured is not configured."""
    resolved = resolve(env(PLEX, **partial))
    assert [s.id for s in resolved.servers] == ['plex']


def test_servers_are_always_in_fixed_order():
    """Fixed order, not discovery order, so a switcher's entries do not
    reshuffle when a user adds a server."""
    resolved = resolve(env(EMBY, JELLYFIN, PLEX))
    assert [s.id for s in resolved.servers] == ['plex', 'jellyfin', 'emby']


def test_data_path_follows_server_id():
    resolved = resolve(env(JELLYFIN))
    assert resolved.servers[0].data_path == 'data/jellyfin'


def test_credentials_never_reach_the_config():
    """The browser gets id, name and dataPath. Nothing else."""
    resolved = resolve(env(PLEX))
    payload = json.dumps(resolved.config_json())
    assert 'ptok' not in payload
    assert '32400' not in payload
    assert set(resolved.config_json()['servers'][0]) == {'id', 'name', 'dataPath'}


# --------------------------------------------------------------------------
# PRIMARY_SERVER resolution — the full table
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('requested', 'servers', 'expected'),
    [
        # Requested server is configured: honoured, whatever else is present.
        ('plex', (PLEX,), 'plex'),
        ('plex', (PLEX, JELLYFIN, EMBY), 'plex'),
        ('jellyfin', (JELLYFIN,), 'jellyfin'),
        ('jellyfin', (PLEX, JELLYFIN), 'jellyfin'),
        ('emby', (EMBY,), 'emby'),
        ('emby', (PLEX, JELLYFIN, EMBY), 'emby'),
        # Requested server has no credentials: fall back in preference order.
        ('plex', (JELLYFIN,), 'jellyfin'),
        ('plex', (EMBY,), 'emby'),
        ('plex', (JELLYFIN, EMBY), 'jellyfin'),
        ('jellyfin', (PLEX,), 'plex'),
        ('jellyfin', (EMBY,), 'emby'),
        ('jellyfin', (PLEX, EMBY), 'plex'),
        ('emby', (PLEX,), 'plex'),
        ('emby', (JELLYFIN,), 'jellyfin'),
        ('emby', (PLEX, JELLYFIN), 'plex'),
        # Unset: first configured server in preference order.
        ('', (PLEX, JELLYFIN, EMBY), 'plex'),
        ('', (JELLYFIN, EMBY), 'jellyfin'),
        ('', (EMBY,), 'emby'),
        # Unrecognised: treated as unset.
        ('kodi', (PLEX,), 'plex'),
        ('kodi', (EMBY,), 'emby'),
    ],
)
def test_primary_server_resolution_table(requested, servers, expected):
    resolved = resolve(env(*servers, PRIMARY_SERVER=requested))
    assert resolved.primary_server == expected


def test_primary_server_is_case_insensitive():
    resolved = resolve(env(JELLYFIN, PRIMARY_SERVER='Jellyfin'))
    assert resolved.primary_server == 'jellyfin'


def test_honoured_request_warns_about_nothing():
    resolved = resolve(env(PLEX, JELLYFIN, PRIMARY_SERVER='jellyfin'))
    assert resolved.warnings == ()


def test_substitution_names_both_servers():
    """The warning text appears in support threads. Preserved verbatim."""
    resolved = resolve(env(JELLYFIN, PRIMARY_SERVER='plex'))
    joined = '\n'.join(resolved.warnings)
    assert 'PRIMARY_SERVER set to' in joined
    assert 'Jellyfin credentials' in joined
    assert "Auto-switching PRIMARY_SERVER to 'jellyfin'" in joined


def test_unset_primary_server_reports_the_default_it_picked():
    resolved = resolve(env(EMBY, PRIMARY_SERVER=''))
    joined = '\n'.join(resolved.warnings)
    assert 'not set or invalid' in joined
    assert 'emby' in joined


# --------------------------------------------------------------------------
# Fatal: nothing configured
# --------------------------------------------------------------------------


def test_no_credentials_raises():
    with pytest.raises(NoServerConfiguredError):
        resolve({})


def test_no_credentials_message_names_every_variable():
    with pytest.raises(NoServerConfiguredError) as excinfo:
        resolve({'APP_TITLE': 'Anything'})
    message = str(excinfo.value)
    for name in (
        'PLEX_URL',
        'PLEX_TOKEN',
        'JELLYFIN_URL',
        'JELLYFIN_TOKEN',
        'EMBY_URL',
        'EMBY_TOKEN',
    ):
        assert name in message


def test_half_configured_everything_still_raises():
    with pytest.raises(NoServerConfiguredError):
        resolve({'PLEX_URL': 'http://plex:32400', 'JELLYFIN_TOKEN': 'jtok'})


# --------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------


def test_defaults_when_nothing_is_set():
    resolved = resolve(env(PLEX))
    assert resolved.app_title == DEFAULT_APP_TITLE == 'Glimpse'
    assert resolved.sort_by_date_added is False
    assert resolved.cron_schedule == DEFAULT_CRON_SCHEDULE


def test_default_cron_schedule_is_every_six_hours():
    # Spelled out rather than inlined: the value contains the character pair
    # that closes a C-style block comment.
    assert DEFAULT_CRON_SCHEDULE == '0 ' + '*/6' + ' * * *'


def test_blank_values_fall_back_to_defaults():
    resolved = resolve(env(PLEX, APP_TITLE='   ', CRON_SCHEDULE=''))
    assert resolved.app_title == 'Glimpse'
    assert resolved.cron_schedule == DEFAULT_CRON_SCHEDULE


def test_overrides_are_honoured():
    resolved = resolve(env(PLEX, APP_TITLE='My Library', CRON_SCHEDULE='30 2 * * *'))
    assert resolved.app_title == 'My Library'
    assert resolved.cron_schedule == '30 2 * * *'


@pytest.mark.parametrize('value', ['true', 'TRUE', 'True', '1', 'yes', 'on'])
def test_sort_by_date_added_accepts_what_users_type(value):
    assert resolve(env(PLEX, SORT_BY_DATE_ADDED=value)).sort_by_date_added is True


@pytest.mark.parametrize('value', ['false', 'FALSE', '0', 'no', '', 'banana'])
def test_sort_by_date_added_is_false_for_anything_else(value):
    assert resolve(env(PLEX, SORT_BY_DATE_ADDED=value)).sort_by_date_added is False


def test_sort_by_date_added_serialises_as_a_json_boolean():
    """Not the string "false" — the frontend branches on it directly, and a
    non-empty string is truthy in JavaScript."""
    payload = json.loads(json.dumps(resolve(env(PLEX)).config_json()))
    assert payload['sortByDateAdded'] is False


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('server', 'creds', 'icon_dir'),
    [
        ('plex', PLEX, '/images'),
        ('jellyfin', JELLYFIN, '/images/jellyfin'),
        ('emby', EMBY, '/images/emby'),
    ],
)
def test_manifest_icons_follow_the_primary_server(server, creds, icon_dir):
    manifest = resolve(env(creds, PRIMARY_SERVER=server)).manifest_json()
    assert [icon['src'] for icon in manifest['icons']] == [
        f'{icon_dir}/android-chrome-192x192.png',
        f'{icon_dir}/android-chrome-512x512.png',
    ]


@pytest.mark.parametrize(
    ('server', 'creds'), [('plex', PLEX), ('jellyfin', JELLYFIN), ('emby', EMBY)]
)
def test_manifest_colors_match_the_theme_table(server, creds):
    manifest = resolve(env(creds, PRIMARY_SERVER=server)).manifest_json()
    assert manifest['theme_color'] == THEME_COLORS[server]
    assert manifest['background_color'] == THEME_COLORS[server]


def test_manifest_is_installable():
    manifest = resolve(env(PLEX)).manifest_json()
    assert manifest['name'] and manifest['short_name']
    assert manifest['start_url'] == '/'
    assert manifest['display'] == 'standalone'
    sizes = {icon['sizes'] for icon in manifest['icons']}
    assert sizes == {'192x192', '512x512'}


def test_the_192_icon_is_maskable():
    manifest = resolve(env(PLEX)).manifest_json()
    icon = next(i for i in manifest['icons'] if i['sizes'] == '192x192')
    assert icon['purpose'] == 'any maskable'


# --------------------------------------------------------------------------
# Crontab
# --------------------------------------------------------------------------


def test_one_cron_entry_per_configured_server():
    crontab = resolve(env(PLEX, EMBY)).crontab()
    entries = [ln for ln in crontab.splitlines() if 'data_fetcher' in ln]
    assert len(entries) == 2
    assert any('/app/data/plex' in ln for ln in entries)
    assert any('/app/data/emby' in ln for ln in entries)


def test_emby_uses_the_jellyfin_fetcher():
    """The APIs are compatible; one adapter has always served both."""
    entry = next(ln for ln in resolve(env(EMBY)).crontab().splitlines() if 'data_fetcher' in ln)
    assert 'jellyfin_data_fetcher.py' in entry
    assert '/app/data/emby' in entry


def test_cron_uses_the_configured_schedule():
    crontab = resolve(env(PLEX, JELLYFIN, CRON_SCHEDULE='30 2 * * *')).crontab()
    for line in (ln for ln in crontab.splitlines() if 'data_fetcher' in ln):
        assert line.startswith('30 2 * * * root ')


def test_exclusions_reach_the_fetcher():
    crontab = resolve(env(PLEX, PLEX_EXCLUDE_LIBRARIES='Home Videos,4')).crontab()
    assert 'PLEX_EXCLUDE_LIBRARIES="Home Videos,4"' in crontab


def test_crontab_ends_with_a_newline():
    """cron silently ignores a final entry with no trailing newline."""
    assert resolve(env(PLEX)).crontab().endswith('\n')


def test_crontab_sets_path():
    assert resolve(env(PLEX)).crontab().startswith('PATH=')


# --------------------------------------------------------------------------
# Writing files
# --------------------------------------------------------------------------


def test_write_files_produces_both_files(tmp_path):
    write_files(resolve(env(PLEX)), tmp_path)
    assert (tmp_path / 'config.json').is_file()
    assert (tmp_path / 'manifest.json').is_file()


def test_generated_output_is_byte_identical_across_runs(tmp_path):
    """A restart with an unchanged environment must not change what is served.

    This is the property the old sed-based entrypoint could not hold, and the
    reason it shipped repair functions for its own output.
    """
    environment = env(PLEX, JELLYFIN, APP_TITLE='My Library')

    first = tmp_path / 'first'
    second = tmp_path / 'second'
    write_files(resolve(environment), first)
    write_files(resolve(environment), second)

    for name in ('config.json', 'manifest.json'):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_rewriting_in_place_is_stable(tmp_path):
    """The real restart case: same directory, written twice."""
    environment = env(JELLYFIN, EMBY, PRIMARY_SERVER='emby')
    write_files(resolve(environment), tmp_path)
    once = (tmp_path / 'config.json').read_bytes()
    write_files(resolve(environment), tmp_path)
    assert (tmp_path / 'config.json').read_bytes() == once


def test_generated_files_are_readable_by_nginx(tmp_path):
    """NamedTemporaryFile creates at 0600; a poster that downloads and then
    403s is this class of bug."""
    write_files(resolve(env(PLEX)), tmp_path)
    for name in ('config.json', 'manifest.json'):
        assert (tmp_path / name).stat().st_mode & 0o044 == 0o044


def test_no_temporary_files_are_left_behind(tmp_path):
    write_files(resolve(env(PLEX)), tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['config.json', 'manifest.json']


def test_written_config_matches_the_resolved_object(tmp_path):
    resolved = resolve(env(PLEX, JELLYFIN, PRIMARY_SERVER='jellyfin'))
    write_files(resolved, tmp_path)
    written = json.loads((tmp_path / 'config.json').read_text())
    assert written == resolved.config_json()
    assert written['primaryServer'] == 'jellyfin'
    assert [s['id'] for s in written['servers']] == ['plex', 'jellyfin']
