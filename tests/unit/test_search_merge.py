"""app.search without a database: prepare(), merge() and search()."""

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app import db
from app.config import Services
from app.search import merge, prepare, search


@pytest.mark.parametrize(
    ('raw', 'prepared'),
    [
        ('NevisWealth', 'NevisWealth'),
        ('  nEvIsWeAlTh  ', 'nEvIsWeAlTh'),
        ('\tJohn\n Doe  ', 'John Doe'),
        ('a\x0bb\x0cc\rd', 'a b c d'),
        ('John\u00a0Doe', 'John Doe'),
        ('a\x1cb', 'a b'),  # Python counts U+001C-U+001F as whitespace too
        (' \t\n ', ''),
    ],
)
def test_prepare_collapses_whitespace_and_trims(raw: str, prepared: str) -> None:
    assert prepare(raw) == prepared


def item(type_: str, id_: object, score: float) -> dict[str, Any]:
    return {'type': type_, 'id': id_, 'score': score, 'match_type': 'exact'}


def test_scores_are_rounded_to_four_decimals() -> None:
    merged = merge([item('client', 'a', 0.123456789), item('client', 'b', 0.85)], 10)
    assert [i['score'] for i in merged] == [0.85, 0.1235]


def test_order_is_score_desc_then_type_then_id() -> None:
    items = [
        item('document', 'a', 0.7),
        item('client', 'c', 0.7),
        item('client', 'b', 0.7),
        item('client', 'z', 0.9),
    ]
    assert [(i['type'], i['id']) for i in merge(items, 10)] == [
        ('client', 'z'),
        ('client', 'b'),
        ('client', 'c'),
        ('document', 'a'),
    ]


def test_ties_are_decided_on_the_rounded_score() -> None:
    # Unrounded, b would come first; both round to 0.7, so the id decides.
    merged = merge([item('client', 'b', 0.70004), item('client', 'a', 0.70001)], 10)
    assert [i['id'] for i in merged] == ['a', 'b']


def test_merge_cuts_to_limit() -> None:
    items = [item('client', f'{n:02d}', n / 100) for n in range(20)]
    assert [i['id'] for i in merge(items, 3)] == ['19', '18', '17']


def test_uuid_ids_are_compared_as_text() -> None:
    low = uuid.UUID('01900000-0000-7000-8000-000000000001')
    high = uuid.UUID('01900000-0000-7000-8000-000000000002')
    assert [i['id'] for i in merge([item('client', high, 0.5), item('client', low, 0.5)], 10)] == [low, high]


def test_search_tags_client_rows_and_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, str, int]] = []

    def fake_search_clients(engine: object, q: str, limit: int) -> list[dict[str, Any]]:
        calls.append((engine, q, limit))
        return [
            {'id': 'b', 'match_type': 'exact', 'score': 0.85000004},
            {'id': 'a', 'match_type': 'fuzzy', 'score': 0.2205},
        ]

    monkeypatch.setattr(db, 'search_clients', fake_search_clients)
    result = search(cast(Services, SimpleNamespace(engine='engine')), 'NevisWealth', 'client', 10)
    assert calls == [('engine', 'NevisWealth', 10)]
    assert [(i['type'], i['id'], i['score']) for i in result] == [
        ('client', 'b', 0.85),
        ('client', 'a', 0.2205),
    ]


def test_type_document_skips_the_client_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object) -> list[dict[str, Any]]:
        raise AssertionError('the client search must not run for type=document')

    monkeypatch.setattr(db, 'search_clients', fail)
    monkeypatch.setattr(db, 'search_documents', lambda *args: [])
    services = SimpleNamespace(
        engine='engine', embedder=SimpleNamespace(embed_query=lambda text: [0.0]), concepts=None
    )
    assert search(cast(Services, services), 'NevisWealth', 'document', 10) == []
