"""Start-up through the lifespan: create the schema on an empty database, load the concept map and the model,
open the connection pool, log one line at start and one at stop; refuse to start when the database cannot be
reached, the concept map is broken or the model is missing; answer 503 when the database goes away while
/health keeps answering."""

import dataclasses
import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import __version__
from app.config import (
    MODEL_REPO,
    MODEL_REVISION,
    PACKAGED_CONCEPTS_FILE,
    RETRY_AFTER_SECONDS,
    SHORT_REVISION_CHARS,
    Services,
    Settings,
)
from app.db import _connection, open_engine
from app.ingest import Concepts
from app.main import create_app
from tests.integration.helpers import new_database

UNREACHABLE = 'postgresql://nevis:nevis@127.0.0.1:1/nevis'  # nothing listens on port 1
PLANTED = 'Zq9planted'  # file content that no error message may repeat


def test_start_creates_the_schema_once_and_logs_one_line_at_start_and_stop(
    admin_dsn: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger='app')
    with new_database(admin_dsn) as dsn:
        # the first start creates the schema, the second finds it; the second runs without a concept map
        for concepts_file in (PACKAGED_CONCEPTS_FILE, ''):
            with TestClient(create_app(Settings(database_url=dsn, concepts_file=concepts_file))) as client:
                assert client.get('/health').json() == {'status': 'ok'}
        threads = Settings(database_url=dsn).embed_threads

    # INFO only: the start without the map also warns that app_meta differs
    lines = [r.getMessage() for r in caplog.records if r.name == 'app.main' and r.levelno == logging.INFO]
    assert [line.split(' | ')[0] for line in lines] == [
        'started: schema: created',
        'stopped',
        'started: schema: present',
        'stopped',
    ]
    entries = len(Concepts.load(PACKAGED_CONCEPTS_FILE).entries)
    model = f'model: {MODEL_REPO}@{MODEL_REVISION[:SHORT_REVISION_CHARS]}, threads {threads}'
    assert f' | concepts: {entries} entries | {model} | ' in lines[0]
    assert f' | concepts: disabled | {model} | ' in lines[2]
    assert 'request body 2097152 bytes, content 50000 characters, q 200 characters' in lines[0]
    assert 'database: pool 8, wait 5 s, connect timeout 3 s, statement timeout 5000 ms' in lines[0]
    assert lines[0].endswith(f' | version {__version__}')


@pytest.mark.usefixtures('admin_dsn')  # runs in compose only, like every integration test
def test_start_fails_at_once_when_the_database_cannot_be_reached() -> None:
    with pytest.raises(OperationalError), TestClient(create_app(Settings(database_url=UNREACHABLE))):
        pass


@pytest.mark.parametrize(
    ('setting', 'name', 'error_type'),
    [
        ('concepts_file', 'invalid.yaml', ValueError),
        ('concepts_file', 'none.yaml', FileNotFoundError),
        ('model_dir', 'empty', FileNotFoundError),  # a directory without the model files
    ],
    ids=['invalid-map', 'missing-map', 'missing-model'],
)
def test_a_broken_concept_map_or_a_missing_model_stops_the_start_naming_the_path(
    fresh_dsn: str, tmp_path: Path, setting: str, name: str, error_type: type[Exception]
) -> None:
    (tmp_path / 'invalid.yaml').write_text(f'- concept: [{PLANTED}\n', encoding='utf-8')
    (tmp_path / 'empty').mkdir()
    path = tmp_path / name
    broken: dict[str, Any] = {setting: str(path)}
    settings = Settings(database_url=fresh_dsn, **broken)

    with pytest.raises(error_type) as error, TestClient(create_app(settings)):
        pass

    assert str(path) in str(error.value)
    assert PLANTED not in str(error.value)


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


def test_database_gone_is_503_on_every_route_while_health_keeps_answering(fresh_dsn: str) -> None:
    app = create_app(Settings(database_url=fresh_dsn))
    with TestClient(app) as client:
        assert client.get('/search', params={'q': 'john'}).status_code == 200
        healthy = app.state.services
        dead_engine = open_engine(Settings(database_url=UNREACHABLE))  # as if the database had gone away
        app.state.services = dataclasses.replace(healthy, engine=dead_engine)
        try:
            responses = {
                'create': client.post(
                    '/clients', json={'first_name': 'Ann', 'last_name': 'Lee', 'email': 'ann@example.com'}
                ),
                'get': client.get('/clients/019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11'),
                'add document': client.post(
                    '/clients/019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11/documents',
                    json={'title': 'Note', 'content': 'Text.'},
                ),
                'get document': client.get(
                    '/clients/019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11/documents/019aa0c6-01a2-7e3f-8a44-9b7d5c2e6f30'
                ),
                'search': client.get('/search', params={'q': 'john'}),
            }
            health = client.get('/health')
        finally:
            app.state.services = healthy
            dead_engine.dispose()

    for route, response in responses.items():
        assert response.status_code == 503, route
        assert response.headers['content-type'] == 'application/problem+json', route
        assert response.headers['retry-after'] == str(RETRY_AFTER_SECONDS), route
        assert response.json()['detail'] == 'The database is unreachable; retry shortly.', route
    assert health.json() == {'status': 'ok'}
