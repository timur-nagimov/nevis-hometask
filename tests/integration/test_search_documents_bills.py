"""`address proof` and `utility bill` on bills that name themselves in other words, and on a long letter
that mentions a bill."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import EXACT_SCORE_MIN
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
def titles(app_client: TestClient) -> dict[str, str]:
    """Document id -> title, for the six documents uploaded once for this module."""
    client_id = post_client(app_client, **JOHN)['id']
    documents = (UTILITY_BILL, PASSPORT, TAX_RETURN, SCAN_0042, ELECTRICITY_BILL, LONG_LETTER)
    return {post_document(app_client, client_id, title, content)['id']: title for title, content in documents}


def hits(app_client: TestClient, titles: dict[str, str], q: str) -> list[tuple[str, dict[str, Any]]]:
    """(title, item) pairs of the documents found for q, best first."""
    response = app_client.get('/search', params={'q': q, 'type': 'document'})
    assert response.status_code == 200, response.text
    return [(titles[item['id']], item) for item in response.json()]


def test_body_only_bill_and_electricity_bill_are_concept_hits(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    found = dict(hits(app_client, titles, 'address proof'))

    for title in ('Scan 0042', 'Electricity bill'):
        assert found[title]['match_type'] == 'concept'
        assert found[title]['score'] >= EXACT_SCORE_MIN


def test_long_letter_is_a_concept_hit_below_every_real_bill(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    ranked = hits(app_client, titles, 'address proof')
    order = [title for title, _ in ranked]

    assert dict(ranked)[LETTER]['match_type'] == 'concept'
    assert all(order.index(bill) < order.index(LETTER) for bill in BILLS)


def test_a_document_close_in_meaning_but_far_below_the_best_is_left_out(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    found = {title for title, _ in hits(app_client, titles, 'utility bill')}

    # the Electricity bill's cosine is above T_STRONG, but more than DELTA below the Utility bill's
    assert found == {'Utility bill', 'Scan 0042', LETTER}
