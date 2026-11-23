"""GET /search on a real database: parameters, the UTF-8 check, the flat item, rounding, order, limit."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import post_client

PEOPLE: dict[str, dict[str, str]] = {
    'john': {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'},
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
    return {key: post_client(app_client, **fields)['id'] for key, fields in PEOPLE.items()}


def search(app_client: TestClient, **params: Any) -> list[dict[str, Any]]:
    response = app_client.get('/search', params=params)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()
    return items


def test_canonical_example_is_a_flat_client_item(app_client: TestClient, ids: dict[str, str]) -> None:
    items = search(app_client, q='NevisWealth')
    assert items == [
        {
            'type': 'client',
            'score': items[0]['score'],
            'match_type': 'exact',
            'id': ids['john'],
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@neviswealth.com',
            'description': '',
            'social_links': [],
        }
    ]
    assert list(items[0])[:3] == ['type', 'score', 'match_type']
    assert 0.5 <= items[0]['score'] <= 1


def test_whitespace_in_q_is_collapsed(app_client: TestClient, ids: dict[str, str]) -> None:
    assert search(app_client, q='\t NevisWealth \n') == search(app_client, q='NevisWealth')
    assert search(app_client, q='Doe\n\tJohn') == search(app_client, q='Doe John')


def test_scores_are_rounded_and_items_ordered(app_client: TestClient, ids: dict[str, str]) -> None:
    items = search(app_client, q='fisher')
    assert [item['id'] for item in items] == [ids['tom'], ids['alice']]
    assert items == sorted(items, key=lambda item: (-item['score'], item['type'], item['id']))
    typo = search(app_client, q='NevisWelth')
    assert [(item['id'], item['match_type']) for item in typo] == [(ids['john'], 'fuzzy')]
    assert all(item['score'] == round(item['score'], 4) for item in items + typo)


def test_limit_cuts_the_list(app_client: TestClient, ids: dict[str, str]) -> None:
    assert [item['id'] for item in search(app_client, q='fisher', limit=1)] == [ids['tom']]
    assert len(search(app_client, q='fisher', limit=50)) == 2


def test_default_limit_is_ten(app_client: TestClient) -> None:
    for n in range(11):
        email = f'client{n}.tenant@example.com'
        post_client(app_client, first_name=f'Client{n}', last_name='Tenant', email=email)
    assert len(search(app_client, q='tenant')) == 10
    assert len(search(app_client, q='tenant', limit=11)) == 11


def test_type_filter(app_client: TestClient, ids: dict[str, str]) -> None:
    assert search(app_client, q='NevisWealth', type='client') == search(app_client, q='NevisWealth')
    assert search(app_client, q='NevisWealth', type='document') == []


@pytest.mark.parametrize(
    'params',
    [
        {},
        {'q': ''},
        {'q': '   '},
        {'q': ' \t\n   '},
        {'q': '\u00a0\u3000'},
        {'q': 'x' * 201},
        {'q': 'john\x00doe'},
        {'q': 'a\x7fb'},
        {'q': 'x', 'limit': 0},
        {'q': 'x', 'limit': 51},
        {'q': 'x', 'limit': 'abc'},
        {'q': 'x', 'type': 'clients'},
    ],
)
def test_bad_parameters_are_422(app_client: TestClient, params: dict[str, Any]) -> None:
    response = app_client.get('/search', params=params)
    assert response.status_code == 422
    assert response.headers['content-type'].startswith('application/problem+json')
    assert all('input' not in error for error in response.json()['errors'])


def test_longest_q_and_largest_limit_are_accepted(app_client: TestClient, ids: dict[str, str]) -> None:
    assert search(app_client, q='x' * 200, limit=50) == []


def test_format_characters_are_allowed_in_q(app_client: TestClient) -> None:
    assert app_client.get('/search', params={'q': 'Zero\u200bWidth'}).status_code == 200


@pytest.mark.parametrize('query_string', ['q=%FF', 'q=%ED%A0%BD', 'q=%FF&limit=abc', 'limit=5&q=John%C3'])
def test_query_string_not_utf8_is_400(app_client: TestClient, query_string: str) -> None:
    response = app_client.get(f'/search?{query_string}')
    assert response.status_code == 400
    assert response.headers['content-type'].startswith('application/problem+json')
    assert response.json()['detail'] == 'The query string is not valid UTF-8.'
