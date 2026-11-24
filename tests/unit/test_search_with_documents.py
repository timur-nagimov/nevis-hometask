"""app.search.search with documents, without a database or the model.

Fakes replace db.search_clients, db.search_documents and the embedder. Results are flat dicts; the route
validates them against list[SearchItem].
"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import numpy.typing as npt
import pytest
from pydantic import TypeAdapter

from app import db
from app.config import EMBEDDING_DIM, EXTRACTIVE, Services
from app.schemas import ClientSearchItem, DocumentSearchItem, SearchItem
from app.search import search

Calls = dict[str, list[dict[str, Any]]]
ITEMS = TypeAdapter(list[SearchItem])
QUERY_VECTOR = np.zeros(EMBEDDING_DIM, dtype=np.float32)


def client_row(n: int, score: float) -> dict[str, Any]:
    """A row as db.search_clients returns it: unrounded score."""
    return {
        'id': uuid.UUID(int=n),
        'match_type': 'exact',
        'score': score,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@neviswealth.com',
        'description': '',
        'social_links': [],
    }


def document_row(n: int, score: float, match_type: str = 'concept') -> dict[str, Any]:
    """A row as db.search_documents returns it: the document's columns, unrounded score, match_type, cos."""
    return {
        'id': uuid.UUID(int=n),
        'score': score,
        'match_type': match_type,
        'cos': 0.48,
        'client_id': uuid.UUID(int=99),
        'title': f'Document {n}',
        'content': 'Utility bill for March 2025.',
        'created_at': datetime(2026, 11, 22, 10, 0, tzinfo=UTC),
        'tags': ['proof of address'],
        'summary': 'Utility bill for March 2025.',
        'summary_method': EXTRACTIVE,
    }


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> npt.NDArray[np.float32]:
        self.queries.append(text)
        return QUERY_VECTOR


class FakeConcepts:
    def alt(self, q: str) -> tuple[str | None, float | None]:
        return ('address proof', 0.96) if q == 'adress proof' else (None, None)


def make_services(concepts: FakeConcepts | None = None) -> Services:
    return cast(Services, SimpleNamespace(engine=object(), embedder=FakeEmbedder(), concepts=concepts))


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Calls:
    """Replaces both searches with fakes that record their arguments."""
    seen: Calls = {'clients': [], 'documents': []}

    def fake_search_clients(engine: object, q: str, limit: int) -> list[dict[str, Any]]:
        seen['clients'].append({'q': q, 'limit': limit})
        return [client_row(3, 0.75), client_row(4, 0.4)]

    def fake_search_documents(
        engine: object,
        q: str,
        qvec: npt.NDArray[np.float32],
        alt: str | None,
        alt_sim: float | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        seen['documents'].append({'q': q, 'qvec': qvec, 'alt': alt, 'alt_sim': alt_sim, 'limit': limit})
        return [document_row(2, 0.74996), document_row(1, 0.75, 'lexical'), document_row(5, 0.2, 'semantic')]

    monkeypatch.setattr(db, 'search_clients', fake_search_clients)
    monkeypatch.setattr(db, 'search_documents', fake_search_documents)
    return seen


def test_clients_and_documents_are_merged_by_rounded_score_then_type_then_id(calls: Calls) -> None:
    items = search(make_services(), 'john', None, 10)

    assert [(item['type'], item['score'], item['id']) for item in items] == [
        ('client', 0.75, uuid.UUID(int=3)),
        ('document', 0.75, uuid.UUID(int=1)),
        ('document', 0.75, uuid.UUID(int=2)),  # 0.74996 is rounded to 0.75 before sorting
        ('client', 0.4, uuid.UUID(int=4)),
        ('document', 0.2, uuid.UUID(int=5)),
    ]


def test_limit_is_passed_to_both_searches_and_cuts_the_merged_list(calls: Calls) -> None:
    items = search(make_services(), 'john', None, 2)

    assert [(item['type'], item['id']) for item in items] == [
        ('client', uuid.UUID(int=3)),
        ('document', uuid.UUID(int=1)),
    ]
    assert calls['clients'] == [{'q': 'john', 'limit': 2}]
    assert [call['limit'] for call in calls['documents']] == [2]


def test_type_client_runs_neither_the_document_search_nor_the_model(calls: Calls) -> None:
    services = make_services()

    items = search(services, 'john', 'client', 10)

    assert {item['type'] for item in items} == {'client'}
    assert calls['documents'] == []
    assert cast(FakeEmbedder, services.embedder).queries == []


def test_type_document_skips_the_client_search_and_embeds_the_query_once(calls: Calls) -> None:
    services = make_services()

    items = search(services, 'john', 'document', 10)

    assert {item['type'] for item in items} == {'document'}
    assert calls['clients'] == []
    assert cast(FakeEmbedder, services.embedder).queries == ['john']
    assert calls['documents'][0]['qvec'] is QUERY_VECTOR


def test_a_document_hit_is_flat_with_a_summary_object_and_without_cos(calls: Calls) -> None:
    hit = search(make_services(), 'john', 'document', 10)[0]

    assert set(hit) == {
        'type',
        'score',
        'match_type',
        'id',
        'client_id',
        'title',
        'content',
        'created_at',
        'tags',
        'summary',
    }
    assert hit['summary'] == {'text': 'Utility bill for March 2025.', 'method': EXTRACTIVE}


def test_the_merged_list_is_valid_for_the_route(calls: Calls) -> None:
    items = ITEMS.validate_python(search(make_services(), 'john', None, 10))

    assert [type(item) for item in items] == [
        ClientSearchItem,
        DocumentSearchItem,
        DocumentSearchItem,
        ClientSearchItem,
        DocumentSearchItem,
    ]


def test_the_spell_correction_is_passed_to_the_document_search(calls: Calls) -> None:
    search(make_services(FakeConcepts()), 'adress proof', 'document', 10)

    assert (calls['documents'][0]['alt'], calls['documents'][0]['alt_sim']) == ('address proof', 0.96)


def test_without_a_concept_map_there_is_no_spell_correction(calls: Calls) -> None:
    search(make_services(), 'adress proof', 'document', 10)

    assert (calls['documents'][0]['alt'], calls['documents'][0]['alt_sim']) == (None, None)
