"""docker-compose.yml is the one file in this repo that every install has a copy of.

Changing it does not break the build, does not fail a lint, and does not show up
in any smoke test — it breaks users, one `docker compose up` at a time, after the
release has already shipped. This test is the only thing that notices.

It is deliberately written as an exact-match assertion rather than a subset
check. A *new* variable is as much of a change as a removed one: it means the app
now reads something a user's existing file does not set, and the default it falls
back to is then a decision that has to be made on purpose. Both directions fail
here.

Failing this test is not a signal to edit the test. It is a signal to go read the
frozen-compose rule in CLAUDE.md and decide, out loud, whether the change is
worth what it costs. If it is, the fixture below moves in the same commit as the
compose file, and the PR body says what an existing user has to do.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip('yaml')

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_PATH = REPO_ROOT / 'docker-compose.yml'
SERVICE_NAME = 'glimpse-media-viewer'

# Every variable docker-compose.yml declares, in the order it declares them.
FROZEN_ENV_KEYS = [
    'PRIMARY_SERVER',
    'PLEX_URL',
    'PLEX_TOKEN',
    'PLEX_EXCLUDE_LIBRARIES',
    'JELLYFIN_URL',
    'JELLYFIN_TOKEN',
    'JELLYFIN_EXCLUDE_LIBRARIES',
    'EMBY_URL',
    'EMBY_TOKEN',
    'EMBY_EXCLUDE_LIBRARIES',
    'CRON_SCHEDULE',
    'TZ',
    'APP_TITLE',
    'SORT_BY_DATE_ADDED',
]


@pytest.fixture(scope='module')
def service():
    compose = yaml.safe_load(COMPOSE_PATH.read_text())
    assert SERVICE_NAME in compose['services'], (
        f'The service is named {SERVICE_NAME!r} in every published compose file. '
        'Renaming it orphans the running container on `docker compose up`.'
    )
    return compose['services'][SERVICE_NAME]


def env_keys(service) -> list[str]:
    """Compose list-form env (`- KEY=value`), reduced to its keys.

    Values are not asserted: they are placeholders a user replaces. The names are
    the contract.
    """
    return [entry.split('=', 1)[0].strip() for entry in service['environment']]


def test_declares_exactly_the_frozen_variables(service):
    assert env_keys(service) == FROZEN_ENV_KEYS


def test_image_name_is_unchanged(service):
    # Users pin `bozodev/glimpse-media-viewer`. The tag moves; the name does not.
    assert service['image'].split(':', 1)[0] == 'bozodev/glimpse-media-viewer'


def test_port_mapping_is_unchanged(service):
    # 9090 is what the README, the screenshots, and every reverse-proxy config a
    # user has written point at.
    assert service['ports'] == ['9090:80']


def test_data_volume_is_unchanged(service):
    # The snapshot lives here. Move it and an upgrade silently starts empty,
    # re-downloading every poster in the library.
    assert './data:/app/data' in service['volumes']


def test_logo_override_stays_available(service):
    """The commented-out logo bind mount is documentation, not dead text.

    It is how a user replaces the logo, and the README points at it. A rewrite
    that relocates web assets has to keep this exact container path working.
    """
    raw = COMPOSE_PATH.read_text()
    assert '/app/web/images/logo.png' in raw
