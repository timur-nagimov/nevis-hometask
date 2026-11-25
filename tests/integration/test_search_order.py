"""SQL truncation and the final merge must agree on ties."""

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import EMBEDDING_DIM, EXTRACTIVE, Services
from app.search import search
from tests.integration.helpers import post_client


def test_tied_clients_keep_the_same_order_at_every_limit(app_client: TestClient) -> None:
    ids = [
        post_client(app_client, first_name='Tieprobe', last_name=name, email=f'{name}@example.com')['id']
        for name in ('Zulu', 'Alpha')
    ]
    responses = [
        app_client.get('/search', params={'q': 'Tieprobe', 'type': 'client', 'limit': limit}).json()
        for limit in (1, 2)
    ]
    assert [item['score'] for item in responses[1]] == [1.0, 1.0]
    assert [item['id'] for item in responses[1]] == sorted(ids)
    assert responses[0] == responses[1][:1]


def test_documents_tied_after_rounding_keep_the_same_order_at_every_limit(
    services: Services, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = db.insert_client(
        services.engine,
        first_name='Document',
        last_name='Owner',
        email='owner@example.com',
        description='',
        social_links=[],
    )
    qvec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    qvec[0] = 1
    monkeypatch.setattr(services.embedder, 'embed_query', lambda q: qvec)
    ids = []
    for cosine in (0.50001, 0.50002):
        vector = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        vector[:2] = [cosine, math.sqrt(1 - cosine * cosine)]
        row = db.insert_document(
            services.engine,
            client_id=client['id'],
            title='Tieprobe',
            content='Tieprobe',
            tags=[],
            tags_text='',
            summary='Tieprobe',
            summary_method=EXTRACTIVE,
            chunks=[(0, vector)],
        )
        ids.append(row['id'])
    one = search(services, 'Tieprobe', 'document', 1)
    two = search(services, 'Tieprobe', 'document', 2)
    assert [item['score'] for item in two] == [0.75, 0.75]
    assert [item['id'] for item in two] == sorted(ids)
    assert one == two[:1]
