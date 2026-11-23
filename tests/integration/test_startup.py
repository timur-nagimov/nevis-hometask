"""Start-up through the lifespan (spec sections 4 and 9, 13.2 B5): migrate, open the pool, log one start-up
line; refuse to start on a database newer than the build or one that cannot be reached; answer 503 when the
database goes away while /health keeps answering."""

import dataclasses
import logging

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Services, Settings
from app.db import MIGRATIONS_DIR, UnknownSchemaVersion, _connection, open_pool
from app.main import ServicesDep, create_app
from tests.integration.helpers import new_database

UNREACHABLE = "postgresql://nevis:nevis@127.0.0.1:1/nevis"  # nothing listens on port 1
# The numbers of the migration files of this build ([1] in step 1). The tests compare against this list,
# never against a literal, so a new migration file (option A adds 002) needs no test change.
ALL_MIGRATIONS = sorted(int(path.name[:3]) for path in MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
NEWER = max(ALL_MIGRATIONS) + 1  # a migration only a newer build has


def test_start_migrates_and_logs_one_startup_line(admin_dsn: str, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app")
    with new_database(admin_dsn) as dsn, TestClient(create_app(Settings(database_url=dsn))) as client:
        assert client.get("/health").json() == {"status": "ok"}

    started = [r.getMessage() for r in caplog.records if r.getMessage().startswith("started:")]
    assert len(started) == 1
    assert f"migrations applied now: {ALL_MIGRATIONS}" in started[0]
    assert "request body 2097152 bytes, content 50000 characters, q 200 characters" in started[0]


def test_start_refuses_a_database_newer_than_the_build(fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn:
        conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (NEWER,))

    with pytest.raises(UnknownSchemaVersion), TestClient(create_app(Settings(database_url=fresh_dsn))):
        pass  # entering the client runs the lifespan


@pytest.mark.usefixtures("admin_dsn")  # runs in compose only, like every integration test
def test_start_fails_at_once_when_the_database_cannot_be_reached() -> None:
    with pytest.raises(psycopg.OperationalError), TestClient(create_app(Settings(database_url=UNREACHABLE))):
        pass


def test_app_client_and_services_share_one_migrated_throwaway_database(
    app_client: TestClient, services: Services
) -> None:
    assert app_client.get("/health").json() == {"status": "ok"}
    with _connection(services.pool) as conn:
        row = conn.execute(
            "SELECT current_database(), (SELECT array_agg(version ORDER BY version) FROM schema_migrations)"
        ).fetchone()

    assert row is not None
    name, versions = row
    assert name.startswith("nevis_t_")  # never the database the API serves
    assert versions == ALL_MIGRATIONS


def test_database_gone_is_503_while_health_keeps_answering(fresh_dsn: str) -> None:
    app = create_app(Settings(database_url=fresh_dsn))

    @app.get("/ping")  # test-only route that uses the database the way the routes of later steps will
    def ping(services: ServicesDep) -> dict[str, int]:
        with _connection(services.pool) as conn:
            row = conn.execute("SELECT 1").fetchone()
        assert row is not None
        return {"one": row[0]}

    with TestClient(app) as client:
        assert client.get("/ping").json() == {"one": 1}
        healthy = app.state.services
        dead_pool = open_pool(UNREACHABLE)  # as if the database had gone away
        app.state.services = dataclasses.replace(healthy, pool=dead_pool)
        try:
            response = client.get("/ping")
            health = client.get("/health")
        finally:
            app.state.services = healthy
            dead_pool.close()

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["retry-after"] == "5"
    assert response.json()["detail"] == "The database is unreachable; retry shortly."
    assert health.json() == {"status": "ok"}
