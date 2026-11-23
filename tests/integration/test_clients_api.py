"""POST /clients and GET /clients/{id} on a real database."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import post_client

JOHN = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'}
FIELDS = ['id', 'first_name', 'last_name', 'email', 'description', 'social_links']


def test_create_returns_201_with_location(app_client: TestClient) -> None:
    body = {
        **JOHN,
        'description': 'Founder\tof a\nlogistics company',
        'social_links': ['https://www.linkedin.com/in/johndoe'],
    }
    response = app_client.post('/clients', json=body)
    assert response.status_code == 201
    created = response.json()
    assert list(created) == FIELDS
    assert created == {'id': created['id'], **body}
    assert str(uuid.UUID(created['id'])) == created['id']
    assert response.headers['location'] == f'/clients/{created["id"]}'


def test_get_returns_the_created_client(app_client: TestClient) -> None:
    created = post_client(app_client, **JOHN)
    response = app_client.get(f'/clients/{created["id"]}')
    assert response.status_code == 200
    assert response.json() == created


def test_optional_fields_default_to_empty(app_client: TestClient) -> None:
    created = post_client(app_client, **JOHN, description=None, social_links=None)
    assert (created['description'], created['social_links']) == ('', [])


def test_values_are_trimmed_and_email_kept_as_sent(app_client: TestClient) -> None:
    created = post_client(
        app_client, first_name='  Mary ', last_name='Major', email=' M.Major@NEVISWEALTH.COM '
    )
    assert (created['first_name'], created['email']) == ('Mary', 'M.Major@NEVISWEALTH.COM')
    assert app_client.get(f'/clients/{created["id"]}').json()['email'] == 'M.Major@NEVISWEALTH.COM'


def test_special_use_domain_is_accepted(app_client: TestClient) -> None:
    created = post_client(app_client, first_name='Owner', last_name='Example', email='owner@example.invalid')
    assert created['email'] == 'owner@example.invalid'


def test_same_email_twice_creates_two_clients(app_client: TestClient) -> None:
    assert post_client(app_client, **JOHN)['id'] != post_client(app_client, **JOHN)['id']


def test_unknown_members_are_ignored(app_client: TestClient) -> None:
    sent_id = '00000000-0000-0000-0000-000000000000'
    created = post_client(app_client, **JOHN, id=sent_id, created_at='yesterday')
    assert created['id'] != sent_id
    assert list(created) == FIELDS


@pytest.mark.parametrize(
    'client_id',
    ['019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11', '123', 'not-a-uuid', '019aa0c56d6e7c7b9d552f1c3b0a4e11'],
)
def test_unknown_or_malformed_id_is_404(app_client: TestClient, client_id: str) -> None:
    response = app_client.get(f'/clients/{client_id}')
    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/problem+json')
    assert response.json()['detail'] == f"Client '{client_id}' does not exist."


@pytest.mark.parametrize(
    'body',
    [
        {'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'},
        {**JOHN, 'email': 'john.doe'},
        {**JOHN, 'first_name': 'Jo\nhn'},
        {**JOHN, 'description': 'a\x00b'},
        {**JOHN, 'social_links': 'https://www.linkedin.com/in/johndoe'},
        [JOHN],
    ],
)
def test_invalid_body_is_422_without_echo(app_client: TestClient, body: object) -> None:
    response = app_client.post('/clients', json=body)
    assert response.status_code == 422
    assert response.headers['content-type'].startswith('application/problem+json')
    errors = response.json()['errors']
    assert errors and all('input' not in error for error in errors)


def test_wrong_media_type_is_415(app_client: TestClient) -> None:
    response = app_client.post('/clients', content=json.dumps(JOHN), headers={'Content-Type': 'text/plain'})
    assert response.status_code == 415


def test_malformed_json_is_400(app_client: TestClient) -> None:
    response = app_client.post(
        '/clients', content=b'{"first_name": "John",', headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 400


def test_body_over_2_mib_is_413(app_client: TestClient) -> None:
    response = app_client.post(
        '/clients', content=b'x' * (2 * 1024 * 1024 + 1), headers={'Content-Type': 'application/json'}
    )
    # The framework may answer in text/plain, so only the status is checked.
    assert response.status_code == 413
