"""GET /search on three short documents: words, concept tags, typos, meaning, junk, and clients in one list.

The module has its own database (app_client), so "nothing found" means nothing at all.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import EXACT_SCORE_MIN, EXTRACTIVE, T_STRONG
from tests.integration.corpus import PASSPORT, TAX_RETURN, UTILITY_BILL
from tests.integration.helpers import post_client, post_document

JOHN = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'}


@pytest.fixture(scope='module')
def titles(app_client: TestClient) -> dict[str, str]:
    """Document id -> title, for the three documents uploaded once for this module."""
    client_id = post_client(app_client, **JOHN)['id']
    documents = (UTILITY_BILL, PASSPORT, TAX_RETURN)
    return {post_document(app_client, client_id, title, content)['id']: title for title, content in documents}


def search(app_client: TestClient, q: str, **params: Any) -> list[dict[str, Any]]:
    response = app_client.get('/search', params={'q': q, **params})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()
    return items


@pytest.mark.parametrize(
    'q', ['address proof', 'proof of address', 'proof of residence', '"address proof"', 'address-proof']
)
def test_address_proof_finds_the_utility_bill_through_its_tags(
    app_client: TestClient, titles: dict[str, str], q: str
) -> None:
    first = search(app_client, q)[0]

    assert (titles.get(first['id']), first['match_type']) == ('Utility bill', 'concept')
    assert first['score'] >= EXACT_SCORE_MIN


def test_utility_bill_is_a_lexical_hit(app_client: TestClient, titles: dict[str, str]) -> None:
    first = search(app_client, 'utility bill')[0]

    assert (titles.get(first['id']), first['match_type']) == ('Utility bill', 'lexical')


def test_id_document_finds_the_passport(app_client: TestClient, titles: dict[str, str]) -> None:
    first = search(app_client, 'ID document')[0]

    assert (titles.get(first['id']), first['match_type']) == ('Passport', 'concept')
    assert first['score'] >= EXACT_SCORE_MIN


@pytest.mark.parametrize('q', ['chocolate cake recipe', 'asdf qwer zxcv', "' OR 1=1 --", '£'])
def test_junk_finds_nothing(app_client: TestClient, titles: dict[str, str], q: str) -> None:
    assert search(app_client, q) == []


def test_sql_in_the_query_is_only_text(app_client: TestClient, titles: dict[str, str]) -> None:
    items = search(app_client, "'; DROP TABLE documents;--")  # search() asserts the 200

    assert all(item['score'] < EXACT_SCORE_MIN for item in items)
    assert search(app_client, 'utility bill') != []  # the table is still there


@pytest.mark.parametrize('q', ['adress proof', 'proof of adress'])
def test_misspelt_concept_phrase_finds_the_bill_as_a_typo(
    app_client: TestClient, titles: dict[str, str], q: str
) -> None:
    first = search(app_client, q)[0]

    assert (titles.get(first['id']), first['match_type']) == ('Utility bill', 'fuzzy')
    assert first['score'] < EXACT_SCORE_MIN


def test_misspelt_title_finds_the_bill_as_a_typo(app_client: TestClient, titles: dict[str, str]) -> None:
    first = search(app_client, 'utilty bill')[0]

    assert (titles.get(first['id']), first['match_type']) == ('Utility bill', 'fuzzy')
    assert first['score'] < EXACT_SCORE_MIN


def test_a_query_close_in_meaning_finds_a_semantic_hit(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    items = search(app_client, 'hmrc letter')

    # the Passport is near enough for a weak guess, but weak guesses come only when nothing is strong
    assert [(titles.get(item['id']), item['match_type']) for item in items] == [('Tax return', 'semantic')]
    assert EXACT_SCORE_MIN * T_STRONG <= items[0]['score'] < EXACT_SCORE_MIN


def test_without_a_strong_hit_the_nearest_document_is_a_weak_guess(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    items = search(app_client, 'gas supplier')

    assert [(titles.get(item['id']), item['match_type']) for item in items] == [('Utility bill', 'semantic')]
    assert items[0]['score'] < EXACT_SCORE_MIN * T_STRONG


def test_clients_and_documents_share_one_ranked_list(app_client: TestClient, titles: dict[str, str]) -> None:
    items = search(app_client, 'john doe')

    assert (items[0]['type'], items[0]['email']) == ('client', JOHN['email'])
    assert {titles.get(item['id']) for item in items[1:]} >= {'Utility bill', 'Passport'}
    assert items == sorted(items, key=lambda item: (-item['score'], item['type'], item['id']))


def test_type_keeps_one_kind_of_item(app_client: TestClient, titles: dict[str, str]) -> None:
    items = search(app_client, 'john doe')

    assert search(app_client, 'john doe', type='client') == [i for i in items if i['type'] == 'client']
    assert search(app_client, 'john doe', type='document') == [i for i in items if i['type'] == 'document']


def test_limit_keeps_the_best_items(app_client: TestClient, titles: dict[str, str]) -> None:
    items = search(app_client, 'john doe')

    assert search(app_client, 'john doe', limit=1) == items[:1]
    assert search(app_client, 'john doe', limit=2) == items[:2]


def test_a_document_item_is_the_stored_document_plus_three_fields(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    item = search(app_client, 'utility bill', type='document')[0]
    document = app_client.get(f'/clients/{item["client_id"]}/documents/{item["id"]}').json()

    assert list(item) == ['type', 'score', 'match_type', *document]
    assert {key: item[key] for key in document} == document  # flat, and rendered exactly like GET
    assert item['summary']['method'] == EXTRACTIVE
    assert 'proof of address' in item['tags']
