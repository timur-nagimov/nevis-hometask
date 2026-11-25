"""The client search (db.search_clients) on a real database."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Services
from tests.integration.helpers import post_client

PEOPLE: dict[str, dict[str, str]] = {
    'john': {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@neviswealth.com',
        'description': 'Long-term client. Prefers quarterly reviews.',
    },
    'zoe': {'first_name': 'Zoë', 'last_name': 'Müller', 'email': 'zoe.mueller@example.ch'},
    'alexei': {
        'first_name': 'Алексей',
        'last_name': 'Смирнов',
        'email': 'a.smirnov@example.ru',
        'description': 'Интересуется облигациями',
    },
    'tom': {'first_name': 'Tom', 'last_name': 'Fisher', 'email': 'tom.fisher@example.com'},
    'alice': {
        'first_name': 'Alice',
        'last_name': 'Brown',
        'email': 'alice.brown@example.com',
        'description': 'Keen fisher; sails on weekends',
    },
}


@pytest.fixture(scope='module')
def ids(app_client: TestClient) -> dict[str, str]:
    """Create the five clients once for this module; map their keys to the new ids."""
    return {key: post_client(app_client, **fields)['id'] for key, fields in PEOPLE.items()}


def found(services: Services, q: str, limit: int = 10) -> list[dict[str, Any]]:
    return db.search_clients(services.engine, q, limit)


def ids_of(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row['id']) for row in rows]


@pytest.mark.parametrize(
    'q', ['NevisWealth', 'neviswealth', 'NEVISWEALTH', 'neviswealth.com', 'john.doe@neviswealth.com']
)
def test_assignment_example_in_several_spellings(services: Services, ids: dict[str, str], q: str) -> None:
    rows = found(services, q)
    assert ids_of(rows) == [ids['john']]
    assert rows[0]['match_type'] == 'exact'
    assert rows[0]['score'] >= 0.5


@pytest.mark.parametrize(
    ('q', 'who'),
    [('wealth', 'john'), ('john.d', 'john'), ('doe@nevis', 'john'), ('Mull', 'zoe'), ('Смир', 'alexei')],
)
def test_part_of_the_email_or_the_name(services: Services, ids: dict[str, str], q: str, who: str) -> None:
    rows = found(services, q)
    assert ids_of(rows) == [ids[who]]
    assert rows[0]['match_type'] == 'exact'


@pytest.mark.parametrize('q', ['John Doe', 'Doe John', 'doe, john', 'john;doe'])
def test_two_words_in_any_order(services: Services, ids: dict[str, str], q: str) -> None:
    rows = found(services, q)
    assert ids_of(rows) == [ids['john']]
    assert rows[0]['match_type'] == 'exact'


@pytest.mark.parametrize('q', ['Zoe Muller', 'zoë müller', 'MULLER ZOE'])
def test_diacritics_are_ignored(services: Services, ids: dict[str, str], q: str) -> None:
    rows = found(services, q)
    assert ids_of(rows) == [ids['zoe']]
    assert rows[0]['match_type'] == 'exact'


@pytest.mark.parametrize('q', ['Смирнов', 'алексей смирнов', 'СМИРНОВ'])
def test_cyrillic_name(services: Services, ids: dict[str, str], q: str) -> None:
    rows = found(services, q)
    assert ids_of(rows) == [ids['alexei']]
    assert rows[0]['match_type'] == 'exact'


def test_description_word_ranks_below_surname(services: Services, ids: dict[str, str]) -> None:
    # Alice is found through her description (weight 0.5); Tom has the word as his surname (weight 1).
    rows = found(services, 'fisher')
    assert ids_of(rows) == [ids['tom'], ids['alice']]
    assert [row['match_type'] for row in rows] == ['exact', 'exact']
    assert rows[0]['score'] > rows[1]['score'] >= 0.5


def test_typo_is_fuzzy_below_one_half(services: Services, ids: dict[str, str]) -> None:
    rows = found(services, 'NevisWelth')
    assert ids_of(rows) == [ids['john']]
    assert rows[0]['match_type'] == 'fuzzy'
    assert 0 < rows[0]['score'] < 0.5


def test_rows_carry_the_api_columns(services: Services, ids: dict[str, str]) -> None:
    row = found(services, 'NevisWealth')[0]
    columns = ['id', 'match_type', 'score', 'first_name', 'last_name', 'email', 'description', 'social_links']
    assert set(row) == set(columns)
    assert (row['first_name'], row['email'], row['social_links']) == ('John', 'john.doe@neviswealth.com', [])


def test_sql_applies_the_limit(services: Services, ids: dict[str, str]) -> None:
    assert ids_of(found(services, 'fisher', limit=1)) == [ids['tom']]
