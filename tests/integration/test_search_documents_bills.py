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


def test_real_bills_rank_first_for_address_proof(app_client: TestClient, titles: dict[str, str]) -> None:
    order = [title for title, _ in hits(app_client, titles, 'address proof')]

    assert set(order[: len(BILLS)]) == set(BILLS)


def test_named_utility_bills_are_returned(app_client: TestClient, titles: dict[str, str]) -> None:
    found = {title for title, _ in hits(app_client, titles, 'utility bill')}

    assert {'Utility bill', 'Scan 0042'} <= found


def test_unrelated_documents_are_excluded_for_utility_bill(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    found = {title for title, _ in hits(app_client, titles, 'utility bill')}

    assert not {'Passport', 'Tax return'} & found


@pytest.mark.xfail(
    strict=True,
    reason='Relative semantic cutoff omits Electricity bill for utility bill; see docs/DESIGN.md section 9',
)
def test_electricity_bill_is_returned_for_utility_bill(
    app_client: TestClient, titles: dict[str, str]
) -> None:
    found = {title for title, _ in hits(app_client, titles, 'utility bill')}

    assert 'Electricity bill' in found


@pytest.mark.parametrize('q', ['address proof', 'utility bill'])
@pytest.mark.xfail(
    strict=True,
    reason='Body mentions give a review letter bill matches and address-proof tags; see README Limits',
)
def test_letter_merely_mentioning_a_bill_is_excluded(
    app_client: TestClient, titles: dict[str, str], q: str
) -> None:
    found = {title for title, _ in hits(app_client, titles, q)}

    assert LETTER not in found
