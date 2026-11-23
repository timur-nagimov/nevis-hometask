"""app_meta records the model revision, the tokenizer settings and the concept map that stored vectors and
tags were built with: written at the first start, compared at every later start. A difference is logged as a
warning; the stored row is kept and the service starts."""

import dataclasses
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, insert, select

from app import db
from app.config import MODEL_REVISION, PACKAGED_CONCEPTS_FILE, TOKENIZER_SETTINGS, Services, Settings
from app.db import AppMetaRow, open_engine
from app.ingest import Concepts
from app.main import check_app_meta, create_app


@pytest.fixture
def engine(fresh_dsn: str) -> Iterator[Engine]:
    opened = open_engine(Settings(database_url=fresh_dsn))
    yield opened
    opened.dispose()


def warning_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]


def test_the_first_start_writes_the_row(fresh_dsn: str, engine: Engine) -> None:
    with TestClient(create_app(Settings(database_url=fresh_dsn))):
        pass

    columns = (AppMetaRow.model_revision, AppMetaRow.tokenizer_settings, AppMetaRow.concepts_sha256)
    with engine.connect() as conn:
        row = conn.execute(select(*columns)).one()
    assert tuple(row) == (MODEL_REVISION, TOKENIZER_SETTINGS, Concepts.load(PACKAGED_CONCEPTS_FILE).sha256)


def test_a_matching_start_is_silent(services: Services, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger='app')

    assert check_app_meta(services) == []
    assert warning_lines(caplog) == []


def test_a_mismatch_logs_a_warning_and_keeps_the_row(
    services: Services, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger='app')
    stored = db.read_app_meta(services.engine)  # written by app_client's start
    without_map = dataclasses.replace(services, concepts=None)  # as if NEVIS_CONCEPTS_FILE were empty

    assert check_app_meta(without_map) == ['concepts_sha256']
    [warning] = warning_lines(caplog)
    assert warning.startswith('app_meta differs in concepts_sha256:')
    assert db.read_app_meta(services.engine) == stored


def test_a_second_write_keeps_the_first_row(services: Services) -> None:
    """Two first starts can both find the table empty; the later write then does nothing."""
    stored = db.read_app_meta(services.engine)

    db.write_app_meta(services.engine, db.AppMeta('other-model', {}, None))

    assert db.read_app_meta(services.engine) == stored


def test_the_service_still_starts_after_a_mismatch_and_names_the_differing_fields(
    fresh_dsn: str, engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    older = insert(AppMetaRow).values(
        model_revision='older-model', tokenizer_settings={'truncation': 128}, concepts_sha256=None
    )
    with engine.begin() as conn:
        conn.execute(older)

    with TestClient(create_app(Settings(database_url=fresh_dsn))) as client:
        assert client.get('/health').status_code == 200

    [warning] = warning_lines(caplog)
    assert warning.startswith('app_meta differs in model_revision, tokenizer_settings, concepts_sha256:')
