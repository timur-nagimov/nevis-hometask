"""`address proof` on bills that name themselves in other words, and on a long letter that mentions a bill."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import EXACT_SCORE_MIN, TAGS_CHUNK_NO, Services
from app.db import DocumentChunkRow, _connection
from tests.integration.corpus import (
    ELECTRICITY_BILL,
    LONG_LETTER,
    PASSPORT,
    SCAN_0042,
    TAX_RETURN,
    UTILITY_BILL,
)
from tests.integration.helpers import post_client, post_document

JOHN = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'}
BILLS = ('Utility bill', 'Scan 0042', 'Electricity bill')
LETTER = LONG_LETTER[0]


@pytest.fixture(scope='module')
def ids(app_client: TestClient) -> dict[str, str]:
    """Title -> document id, for the six documents uploaded once for this module."""
    client_id = post_client(app_client, **JOHN)['id']
    documents = (UTILITY_BILL, PASSPORT, TAX_RETURN, SCAN_0042, ELECTRICITY_BILL, LONG_LETTER)
    return {title: post_document(app_client, client_id, title, content)['id'] for title, content in documents}


def address_proof(app_client: TestClient, ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    """(title, item) pairs of `address proof`, best first."""
    response = app_client.get('/search', params={'q': 'address proof', 'type': 'document'})
    assert response.status_code == 200, response.text
    title_of = {document_id: title for title, document_id in ids.items()}
    return [(title_of[item['id']], item) for item in response.json()]


def test_body_only_bill_and_electricity_bill_are_concept_hits(
    app_client: TestClient, ids: dict[str, str]
) -> None:
    found = dict(address_proof(app_client, ids))

    for title in ('Scan 0042', 'Electricity bill'):
        assert found[title]['match_type'] == 'concept'
        assert found[title]['score'] >= EXACT_SCORE_MIN


def test_long_letter_is_a_concept_hit_below_every_real_bill(
    app_client: TestClient, ids: dict[str, str]
) -> None:
    ranked = address_proof(app_client, ids)
    titles = [title for title, _ in ranked]

    assert dict(ranked)[LETTER]['match_type'] == 'concept'
    assert all(titles.index(bill) < titles.index(LETTER) for bill in BILLS)


def test_only_short_documents_get_the_tags_chunk(services: Services, ids: dict[str, str]) -> None:
    """Why the letter ranks lower: it carries the tag, but a document over SHORT_DOC_WORDS words gets the tags
    chunk only for concepts in its title."""
    statement = select(DocumentChunkRow.document_id).where(DocumentChunkRow.chunk_no == TAGS_CHUNK_NO)
    with _connection(services.engine) as conn:
        with_tags_chunk = {str(document_id) for document_id in conn.execute(statement).scalars()}
    titles = {title for title, document_id in ids.items() if document_id in with_tags_chunk}

    assert set(BILLS) <= titles
    assert LETTER not in titles
