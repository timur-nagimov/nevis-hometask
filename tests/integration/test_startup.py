"""Start-up through the lifespan: create the schema on an empty database, open the connection pool, log one
start-up line; refuse to start when the database cannot be reached; answer 503 when the database goes away
while /health keeps answering."""

import dataclasses
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import Services, Settings
from app.db import _connection, open_engine
from app.main import ServicesDep, create_app
from tests.integration.helpers import new_database

UNREACHABLE = 'postgresql://nevis:nevis@127.0.0.1:1/nevis'  # nothing listens on port 1


def test_start_creates_the_schema_once_and_logs_one_startup_line(
    admin_dsn: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger='app')
    with new_database(admin_dsn) as dsn:
        for _ in range(2):  # the first start creates the schema, the second finds it
            with TestClient(create_app(Settings(database_url=dsn))) as client:
                assert client.get('/health').json() == {'status': 'ok'}

    started = [r.getMessage() for r in caplog.records if r.getMessage().startswith('started:')]
    assert [line.split(' | ')[0] for line in started] == [
        'started: schema: created',
        'started: schema: present',
    ]
    assert 'request body 2097152 bytes, content 50000 characters, q 200 characters' in started[0]
    assert 'database: pool 8, wait 5 s, connect timeout 3 s, statement timeout 5000 ms' in started[0]


@pytest.mark.usefixtures('admin_dsn')  # runs in compose only, like every integration test
def test_start_fails_at_once_when_the_database_cannot_be_reached() -> None:
    with pytest.raises(OperationalError), TestClient(create_app(Settings(database_url=UNREACHABLE))):
        pass


def test_app_client_and_services_share_one_throwaway_database_with_the_schema(
    app_client: TestClient, services: Services
) -> None:
    assert app_client.get('/health').json() == {'status': 'ok'}
    with _connection(services.engine) as conn:
        name, has_schema = conn.execute(
            text("SELECT current_database(), to_regclass('public.app_meta') IS NOT NULL")
        ).one()

    assert name.startswith('nevis_t_')  # never the database the API serves
    assert has_schema is True


def test_database_gone_is_503_while_health_keeps_answering(fresh_dsn: str) -> None:
    app = create_app(Settings(database_url=fresh_dsn))

    @app.get('/ping')  # test-only route that uses the database the way the routes of later steps will
    def ping(services: ServicesDep) -> dict[str, int]:
        with _connection(services.engine) as conn:
            one: int = conn.execute(text('SELECT 1')).scalar_one()
        return {'one': one}

    with TestClient(app) as client:
        assert client.get('/ping').json() == {'one': 1}
        healthy = app.state.services
        dead_engine = open_engine(Settings(database_url=UNREACHABLE))  # as if the database had gone away
        app.state.services = dataclasses.replace(healthy, engine=dead_engine)
        try:
            response = client.get('/ping')
            health = client.get('/health')
        finally:
            app.state.services = healthy
            dead_engine.dispose()

    assert response.status_code == 503
    assert response.headers['content-type'] == 'application/problem+json'
    assert response.headers['retry-after'] == '5'
    assert response.json()['detail'] == 'The database is unreachable; retry shortly.'
    assert health.json() == {'status': 'ok'}
