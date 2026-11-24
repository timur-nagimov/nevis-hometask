"""A known limitation, recorded: a courier's "Proof of delivery" ranks among the bills for `address proof`.

Its text ("... sent to the home address ...") holds every word of `address proof` and `proof of address`, so
it is a lexical hit, while the bills are concept hits through their "proof of address" tag. Lexical and
concept hits get the same score for the same cosine, so only meaning orders them, and nothing in the design
tells a delivery note from address evidence. The test therefore asserts how each document is found, not the
order, and prints the note's rank and its score margin to the lower bill (run with -s). Measured: rank 3 of 3
for both queries; margin +0.0101 for `address proof` and +0.0043 for `proof of address`. A negative margin
would put the note above a bill.
"""

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
def test_proof_of_delivery_is_found_by_its_words_and_the_bills_by_their_tags(
    app_client: TestClient, suite_id_of: dict[str, str], q: str
) -> None:
    response = app_client.get('/search', params={'q': q, 'type': 'document'})
    assert response.status_code == 200, response.text
    items = response.json()
    ranked = [suite_id_of[item['id']] for item in items]
    found = {suite_id_of[item['id']]: item for item in items}

    assert {*BILLS, TRAP} <= found.keys(), ranked
    for bill in BILLS:
        assert found[bill]['match_type'] == 'concept'
    assert found[TRAP]['match_type'] == 'lexical'

    # recorded, not asserted
    trap_score = found[TRAP]['score']
    margin = min(found[bill]['score'] for bill in BILLS) - trap_score
    print(
        f"\nTRAP q={q!r}: 'Proof of delivery' rank {ranked.index(TRAP) + 1} of {len(ranked)}, "
        f'score {trap_score:.4f}, margin to the lower bill {margin:+.4f}'
    )
