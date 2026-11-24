"""The document search (db.search_documents) on a real database.

Scores are unrounded here: the API rounds them (app.search.merge).
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import DEFAULT_LIMIT, EXACT_SCORE_MIN, EXTRACTIVE, FUZZY_SCORE_MAX, Services
from tests.integration.corpus import PASSPORT, UTILITY_BILL
from tests.integration.helpers import post_client, post_document

JOHN = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'}
DOCUMENT_COLUMNS = {'id', 'client_id', 'title', 'content', 'created_at', 'tags', 'summary', 'summary_method'}


@pytest.fixture(scope='module')
def ids(app_client: TestClient) -> dict[str, str]:
    """Title -> document id: the utility bill and the passport, both mention John Doe."""
    client_id = post_client(app_client, **JOHN)['id']
    documents = (UTILITY_BILL, PASSPORT)
    return {title: post_document(app_client, client_id, title, content)['id'] for title, content in documents}


def rows(
    services: Services,
    q: str,
    alt: str | None = None,
    alt_sim: float | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    return db.search_documents(services.engine, q, services.embedder.embed_query(q), alt, alt_sim, limit)


def test_a_row_has_score_match_type_cos_and_the_document_columns(
    services: Services, ids: dict[str, str]
) -> None:
    row = rows(services, 'utility bill')[0]

    assert set(row) == DOCUMENT_COLUMNS | {'score', 'match_type', 'cos'}
    assert str(row['id']) == ids['Utility bill']
    assert row['match_type'] == 'lexical'
    assert EXACT_SCORE_MIN <= row['score'] <= 1
    assert (row['title'], row['summary_method']) == ('Utility bill', EXTRACTIVE)
    assert 'proof of address' in row['tags']


def test_alt_and_alt_sim_drive_the_typo_leg(services: Services, ids: dict[str, str]) -> None:
    assert all(row['match_type'] != 'fuzzy' for row in rows(services, 'adress proof'))

    row = rows(services, 'adress proof', alt='address proof', alt_sim=0.96)[0]

    assert str(row['id']) == ids['Utility bill']
    assert row['match_type'] == 'fuzzy'
    assert row['score'] == pytest.approx(FUZZY_SCORE_MAX * 0.96)


def test_rows_are_best_first_and_limited(services: Services, ids: dict[str, str]) -> None:
    both = rows(services, 'john doe')
    scores = [row['score'] for row in both]

    assert {str(row['id']) for row in both} == set(ids.values())
    assert scores == sorted(scores, reverse=True)
    assert rows(services, 'john doe', limit=1) == both[:1]
