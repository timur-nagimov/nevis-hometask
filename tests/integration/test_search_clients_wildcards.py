"""`_`, `%` and `\\` in a query match only themselves: the client search escapes the LIKE wildcards.

Each case has a second client that the query would find if the escaping were broken.
"""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Services
from tests.integration.helpers import post_client

PEOPLE: dict[str, dict[str, str]] = {
    'underscore': {'first_name': 'Una', 'last_name': 'Score', 'email': 'a_b@example.com'},
    'any_letter': {'first_name': 'Paul', 'last_name': 'Lain', 'email': 'axb@example.com'},
    'percent': {
        'first_name': 'Percy',
        'last_name': 'Cent',
        'email': 'percy@example.com',
        'description': '100% equity',
    },
    'more_digits': {
        'first_name': 'Dina',
        'last_name': 'Gits',
        'email': 'dina@example.com',
        'description': '1000 equity',
    },
    'backslash': {
        'first_name': 'Bea',
        'last_name': 'Slash',
        'email': 'bea@example.com',
        'description': 'share c:\\temp',
    },
    'no_backslash': {
        'first_name': 'Nora',
        'last_name': 'Plain',
        'email': 'nora@example.com',
        'description': 'share c:temp',
    },
}


@pytest.fixture(scope='module')
def ids(app_client: TestClient) -> dict[str, str]:
    return {key: post_client(app_client, **fields)['id'] for key, fields in PEOPLE.items()}


@pytest.mark.parametrize(
    ('q', 'who'), [('a_b', 'underscore'), ('100%', 'percent'), ('c:\\temp', 'backslash')]
)
def test_a_wildcard_character_matches_only_itself(
    services: Services, ids: dict[str, str], q: str, who: str
) -> None:
    rows = db.search_clients(services.engine, q, 10)
    assert [str(row['id']) for row in rows] == [ids[who]]
    assert rows[0]['match_type'] == 'exact'
