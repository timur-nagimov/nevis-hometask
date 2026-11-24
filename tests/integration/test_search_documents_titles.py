"""Stop-word titles, queries without a searchable word, identifiers and accents."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import EXACT_SCORE_MIN
from tests.integration.corpus import LETTER_OF_WISHES, POLICY, WILL, ZURICH
from tests.integration.helpers import post_client, post_document

JOHN = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'}


@pytest.fixture(scope='module')
def titles(app_client: TestClient) -> dict[str, str]:
    """Document id -> title, for the four documents uploaded once for this module."""
    client_id = post_client(app_client, **JOHN)['id']
    documents = (WILL, LETTER_OF_WISHES, POLICY, ZURICH)
    return {post_document(app_client, client_id, title, content)['id']: title for title, content in documents}


def documents(app_client: TestClient, q: str) -> list[dict[str, Any]]:
    """The document hits only: `a` occurs in John Doe's e-mail address and would find him."""
    response = app_client.get('/search', params={'q': q, 'type': 'document'})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()
    return items


@pytest.mark.parametrize('q', ['will', 'a will'])  # a one-letter piece is not a query word
def test_will_finds_the_document_titled_will(app_client: TestClient, titles: dict[str, str], q: str) -> None:
    items = documents(app_client, q)

    assert [(titles[item['id']], item['match_type']) for item in items] == [('Will', 'lexical')]
    assert items[0]['score'] >= EXACT_SCORE_MIN


@pytest.mark.parametrize('q', ['of', 'a', '????'])
def test_a_query_without_a_searchable_word_finds_nothing(
    app_client: TestClient, titles: dict[str, str], q: str
) -> None:
    assert documents(app_client, q) == []


@pytest.mark.parametrize('q', ['LV-7734-0921-KX', '7734'])
def test_an_identifier_is_found_whole_and_by_a_fragment(
    app_client: TestClient, titles: dict[str, str], q: str
) -> None:
    first = documents(app_client, q)[0]

    assert (titles[first['id']], first['match_type']) == (POLICY[0], 'lexical')


def test_an_accented_title_is_found_by_its_accented_word(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    first = documents(app_client, 'zürich')[0]

    assert (titles[first['id']], first['match_type']) == (ZURICH[0], 'lexical')
