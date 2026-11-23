"""How every database connection is opened: libpq options from Settings, no database needed."""

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool

from app.config import Settings
from app.db import connection_info, create_schema, open_engine

URL = 'postgresql://u@h/d'


def test_defaults() -> None:
    parameters = conninfo_to_dict(connection_info(Settings(database_url=URL)))

    assert parameters['options'] == '-c statement_timeout=5000 -c pg_trgm.word_similarity_threshold=0.6'
    assert (parameters['connect_timeout'], parameters['keepalives_idle']) == ('3', '30')
    assert parameters['tcp_user_timeout'] == '10000'
    assert parameters['fallback_application_name'] == 'nevis-search'


def test_the_timeouts_come_from_the_settings() -> None:
    settings = Settings(database_url=URL, db_connect_timeout_seconds=10, db_statement_timeout_ms=300)

    parameters = conninfo_to_dict(connection_info(settings))

    assert parameters['connect_timeout'] == '10'
    assert str(parameters['options']).startswith('-c statement_timeout=300 ')


def test_options_of_the_url_are_kept_before_ours() -> None:
    settings = Settings(database_url=URL + '?options=-c%20search_path%3Dapp')

    options = conninfo_to_dict(connection_info(settings))['options']

    assert options == '-c search_path=app -c statement_timeout=5000 -c pg_trgm.word_similarity_threshold=0.6'


def test_the_pool_comes_from_the_settings() -> None:
    engine = open_engine(Settings(database_url=URL, db_pool_size=3, db_pool_timeout_seconds=1.5))

    assert isinstance(engine.pool, QueuePool)
    assert (engine.pool.size(), engine.pool.timeout()) == (3, 1.5)  # no database touched


def test_start_up_and_pool_connect_the_same_way(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_connect(conninfo: str) -> psycopg.Connection:
        calls.append(conninfo)
        raise psycopg.OperationalError('no server here')

    monkeypatch.setattr(psycopg, 'connect', fake_connect)
    settings = Settings(database_url=URL)

    with pytest.raises(OperationalError):
        create_schema(settings)
    with pytest.raises(OperationalError):
        open_engine(settings).connect()

    assert calls == [connection_info(settings)] * 2
