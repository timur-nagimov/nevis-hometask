"""Address-proof queries should find bills and exclude a courier's proof of delivery."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import post_client, post_document

SUITE = Path(__file__).resolve().parents[2] / 'testset' / 'suites' / 'tools-mini-6.json'
BILLS = ('d01', 'd05')  # "Utility bill", "Scan 0042"
TRAP = 'd04'  # "Proof of delivery"


@pytest.fixture(scope='module')
def suite_id_of(app_client: TestClient) -> dict[str, str]:
    """API document id -> suite id, for the suite's clients and documents posted once, in file order."""
    corpus = json.loads(SUITE.read_text(encoding='utf-8'))['corpus']
    client_ids: dict[str, str] = {}
    for client in corpus['clients']:
        client_ids[client['id']] = post_client(app_client, **client)['id']  # the API ignores the suite's id
    suite_id_of: dict[str, str] = {}
    for document in corpus['documents']:
        client_id = client_ids[document['client_id']]
        created = post_document(app_client, client_id, document['title'], document['content'])
        suite_id_of[created['id']] = document['id']
    return suite_id_of


@pytest.mark.parametrize('q', ['address proof', 'proof of address'])
def test_bills_are_found_by_their_address_proof_tags(
    app_client: TestClient, suite_id_of: dict[str, str], q: str
) -> None:
    response = app_client.get('/search', params={'q': q, 'type': 'document'})
    assert response.status_code == 200, response.text
    items = response.json()
    ranked = [suite_id_of[item['id']] for item in items]
    found = {suite_id_of[item['id']]: item for item in items}

    assert set(BILLS) <= found.keys(), ranked
    for bill in BILLS:
        assert found[bill]['match_type'] == 'concept'


@pytest.mark.parametrize('q', ['address proof', 'proof of address'])
@pytest.mark.xfail(
    strict=True,
    reason='Scattered lexical words return proof of delivery as address proof; see README Limits',
)
def test_proof_of_delivery_is_excluded_from_address_proof(
    app_client: TestClient, suite_id_of: dict[str, str], q: str
) -> None:
    response = app_client.get('/search', params={'q': q, 'type': 'document'})
    assert response.status_code == 200, response.text
    found = {suite_id_of[item['id']] for item in response.json()}

    assert TRAP not in found
