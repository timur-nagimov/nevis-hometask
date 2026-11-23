"""Queries that must find nothing. This module's database holds only John Doe."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Services
from tests.integration.helpers import post_client


@pytest.fixture(scope='module', autouse=True)
def john(app_client: TestClient) -> dict[str, Any]:
    return post_client(app_client, first_name='John', last_name='Doe', email='john.doe@neviswealth.com')


# Without escaping, `%` and `_` would be LIKE wildcards and match every client.
@pytest.mark.parametrize('q', ["' OR 1=1 --", "'; DROP TABLE clients;--", '" OR ""="', '%', '_', '\\', '*'])
def test_injection_and_wildcards_find_nothing(
    app_client: TestClient, services: Services, john: dict[str, Any], q: str
) -> None:
    assert db.search_clients(services.pool, q, 10) == []
    assert app_client.get(f'/clients/{john["id"]}').status_code == 200  # the table is still there


def test_short_typo_is_not_searched_for_typos(services: Services) -> None:
    # "jhon" is not a substring of the record, and the typo tier needs at least 5 letters or digits.
    assert db.search_clients(services.pool, 'jhon', 10) == []
