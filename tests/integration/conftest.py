"""Fixtures of the integration tests (DEVELOPMENT_PLAN.md section 4.3). They need the compose database:

    docker compose up -d db && docker compose --profile test run --rm --no-deps tests

Every test database is a throw-away `nevis_t_<hex>` on the compose server, dropped afterwards; the
database the API serves (`nevis`) is never touched. Without NEVIS_DATABASE_URL these tests are skipped.
"""

import os
import time
from collections.abc import Iterator

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from app.db import migrate
from tests.integration.helpers import new_database


@pytest.fixture(scope="session")
def admin_dsn() -> str:
    """NEVIS_DATABASE_URL with the database name replaced by `postgres`. Waits up to 60 s for the server:
    podman-compose's `run` does not wait for the db health check."""
    url = os.environ.get("NEVIS_DATABASE_URL")
    if not url:
        pytest.skip("needs PostgreSQL: docker compose --profile test run --rm --no-deps tests")
    dsn = make_conninfo(url, dbname="postgres")
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
    """A new empty database `nevis_t_<hex>`, migrated; dropped after the test."""
    with new_database(admin_dsn) as dsn:
        migrate(dsn)
        yield dsn
