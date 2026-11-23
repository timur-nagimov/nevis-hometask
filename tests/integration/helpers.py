"""Helpers for the integration tests."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo


@contextmanager
def new_database(admin_dsn: str, options: str = '') -> Iterator[str]:
    """An empty database `nevis_t_<hex>`, created with `CREATE DATABASE ... <options>` and dropped when the
    block ends. Yields its connection string."""
    name = f'nevis_t_{uuid.uuid4().hex[:12]}'
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {} ' + options).format(sql.Identifier(name)))
    try:
        yield make_conninfo(admin_dsn, dbname=name)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


def post_client(client: TestClient, **fields: Any) -> dict[str, Any]:
    """POST /clients with exactly these fields; assert 201 and return the created client."""
    response = client.post('/clients', json=fields)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def post_document(client: TestClient, client_id: str, title: str, content: str) -> dict[str, Any]:
    """POST a document to this client; assert 201 and return the created document."""
    response = client.post(f'/clients/{client_id}/documents', json={'title': title, 'content': content})
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created
