"""Fixtures of the integration tests. They need the compose database:

    docker compose up -d db && docker compose --profile test run --rm --no-deps tests

Every test database is a throw-away `nevis_t_<hex>` on the compose server, dropped afterwards; the
database the API serves (`nevis`) is never touched. Without NEVIS_DATABASE_URL these tests are skipped.
"""

import os
import time
from collections.abc import Iterator
from typing import cast

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from app.config import Services, Settings
from app.db import create_schema
from app.main import create_app
from tests.integration.helpers import new_database


@pytest.fixture(scope='session')
def admin_dsn() -> str:
    """NEVIS_DATABASE_URL with the database name replaced by `postgres`. Waits up to 60 s for the server:
    podman-compose's `run` does not wait for the db health check."""
    url = os.environ.get('NEVIS_DATABASE_URL')
    if not url:
        pytest.skip('needs PostgreSQL: docker compose --profile test run --rm --no-deps tests')
    dsn = make_conninfo(url, dbname='postgres')
    deadline = time.monotonic() + 60
    while True:
        try:
            psycopg.connect(dsn, connect_timeout=3).close()
            return dsn
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture
def fresh_dsn(admin_dsn: str) -> Iterator[str]:
    """A new database `nevis_t_<hex>` with the schema; dropped after the test."""
    with new_database(admin_dsn) as dsn:
        create_schema(Settings(database_url=dsn))
        yield dsn


@pytest.fixture(scope='module')
def app_dsn(admin_dsn: str) -> Iterator[str]:
    """The database of this module's `app_client`; the application's own lifespan creates its schema."""
    with new_database(admin_dsn) as dsn:
        yield dsn


@pytest.fixture(scope='module')
def app_client(app_dsn: str) -> Iterator[TestClient]:
    """The real application on its own database with the lifespan running (schema, concept map, model,
    pool)."""
    with TestClient(create_app(Settings(database_url=app_dsn))) as client:
        yield client


@pytest.fixture(scope='module')
def services(app_client: TestClient) -> Services:
    """The bundle `build_services` made in app_client's lifespan: same database and pool, the model and the
    shipped concept map. Reused rather than built twice: loading the model takes time."""
    built: Services = cast(FastAPI, app_client.app).state.services
    return built
