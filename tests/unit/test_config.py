"""Settings come from NEVIS_* variables; the constants keep their expected values."""

import dataclasses
import os
from pathlib import Path
from typing import cast

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine

from app import config
from app.config import Services, Settings


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://ignored/unprefixed')  # only NEVIS_* names are read

    with pytest.raises(ValidationError) as error:
        Settings()

    assert [e['loc'] for e in error.value.errors()] == [('database_url',)]


@pytest.mark.parametrize(
    'url',
    [
        'postgresql+psycopg://u:Zq9xW@db/nevis',  # a SQLAlchemy URL, not one libpq reads
        'postgresql://u:Zq9%xW@db/nevis',  # a bad percent escape
        'postgresql://u:Zq9@xW@db/nevis',  # an unencoded @ in the password
        'postgresql://u:Zq9/xW@db/nevis',  # an unencoded / in the password
        'postgresql://u:Zq9 xW@db/nevis',  # a space in the password
        '',
    ],
)
def test_database_url_libpq_cannot_read_is_refused_without_quoting_it(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv('NEVIS_DATABASE_URL', url)

    with pytest.raises(ValidationError) as error:
        Settings()

    assert [e['loc'] for e in error.value.errors()] == [('database_url',)]
    assert 'Zq9' not in str(error.value)
    assert 'xW' not in str(error.value)


@pytest.mark.parametrize(
    'url',
    [
        'host=db port=5432 dbname=nevis user=u password=p@ss',
        'postgresql://u:p@db:5432/nevis?options=-c%20search_path%3Dapp',
    ],
)
def test_url_and_key_value_forms_are_accepted(url: str) -> None:
    assert Settings(database_url=url).database_url.get_secret_value() == url


def test_settings_and_services_never_print_the_database_url() -> None:
    settings = Settings(database_url='postgresql://u:S3cret@db/nevis')
    services = Services(settings=settings, engine=cast(Engine, None), embedder=None, concepts=None)

    for text in (repr(settings), str(settings.model_dump()), repr(services)):
        assert 'S3cret' not in text


def test_a_settings_error_prints_no_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEVIS_MODEL_DIR', '/planted')  # NEVIS_DATABASE_URL is missing

    with pytest.raises(ValidationError) as error:
        Settings()

    assert 'planted' not in str(error.value)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEVIS_DATABASE_URL', 'postgresql://u:p@db:5432/nevis')

    settings = Settings()

    assert settings.database_url.get_secret_value() == 'postgresql://u:p@db:5432/nevis'
    assert settings.model_dir == '/opt/models/leaf-ir'
    assert settings.embed_threads == min(4, os.process_cpu_count() or 1)
    assert Path(settings.concepts_file) == Path(config.__file__).parent / 'data' / 'concepts.yaml'
    assert settings.max_content_chars == 50_000
    assert settings.log_level == 'INFO'
    database = (
        settings.db_pool_size,
        settings.db_pool_timeout_seconds,
        settings.db_connect_timeout_seconds,
        settings.db_statement_timeout_ms,
    )
    assert database == (8, 5.0, 3, 5000)


def test_every_setting_is_read_from_its_nevis_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEVIS_DATABASE_URL', 'postgresql://other/db')
    monkeypatch.setenv('NEVIS_MODEL_DIR', '/models')
    monkeypatch.setenv('NEVIS_EMBED_THREADS', '1')
    monkeypatch.setenv('NEVIS_CONCEPTS_FILE', '/etc/concepts.yaml')
    monkeypatch.setenv('NEVIS_MAX_CONTENT_CHARS', '1000')
    monkeypatch.setenv('NEVIS_LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('NEVIS_DB_POOL_SIZE', '2')
    monkeypatch.setenv('NEVIS_DB_POOL_TIMEOUT_SECONDS', '0.5')
    monkeypatch.setenv('NEVIS_DB_CONNECT_TIMEOUT_SECONDS', '10')
    monkeypatch.setenv('NEVIS_DB_STATEMENT_TIMEOUT_MS', '300')

    assert Settings().model_dump() == {
        'database_url': SecretStr('postgresql://other/db'),
        'db_pool_size': 2,
        'db_pool_timeout_seconds': 0.5,
        'db_connect_timeout_seconds': 10,
        'db_statement_timeout_ms': 300,
        'model_dir': '/models',
        'embed_threads': 1,
        'concepts_file': '/etc/concepts.yaml',
        'max_content_chars': 1000,
        'log_level': 'DEBUG',
    }


def test_empty_concepts_file_switches_concept_tagging_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """`NEVIS_CONCEPTS_FILE=` must stay empty, not fall back to the packaged file."""
    monkeypatch.setenv('NEVIS_DATABASE_URL', 'postgresql://u:p@db:5432/nevis')
    monkeypatch.setenv('NEVIS_CONCEPTS_FILE', '')

    assert Settings().concepts_file == ''


def test_invalid_values_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEVIS_DATABASE_URL', 'postgresql://u:p@db:5432/nevis')
    monkeypatch.setenv('NEVIS_DB_POOL_SIZE', '0')  # SQLAlchemy would read 0 as no limit
    monkeypatch.setenv('NEVIS_DB_POOL_TIMEOUT_SECONDS', '0')
    monkeypatch.setenv('NEVIS_DB_CONNECT_TIMEOUT_SECONDS', '1')  # libpq counts less than 2 as 2
    monkeypatch.setenv('NEVIS_DB_STATEMENT_TIMEOUT_MS', '0')  # PostgreSQL reads 0 as no limit
    monkeypatch.setenv('NEVIS_EMBED_THREADS', '0')
    monkeypatch.setenv('NEVIS_LOG_LEVEL', 'LOUD')

    with pytest.raises(ValidationError) as error:
        Settings()

    assert [e['loc'] for e in error.value.errors()] == [
        ('db_pool_size',),
        ('db_pool_timeout_seconds',),
        ('db_connect_timeout_seconds',),
        ('db_statement_timeout_ms',),
        ('embed_threads',),
        ('log_level',),
    ]


def test_constants_keep_their_values() -> None:
    assert (config.T_STRONG, config.DELTA, config.T_FALLBACK, config.K_FALLBACK) == (0.40, 0.08, 0.32, 3)
    assert (config.TAU_TITLE, config.MIN_FUZZY_CHARS, config.SPELL_CUTOFF) == (0.60, 5, 0.90)
    assert (config.SHORT_DOC_WORDS, config.CHUNK_WORDS, config.SUMMARY_CHARS) == (200, 200, 300)
    assert config.EMBED_BATCH == 4
    assert config.QUERY_PREFIX == 'Represent this sentence for searching relevant passages: '
    assert config.MAX_BODY_BYTES == 2 * 1024 * 1024
    assert (config.MAX_Q_CHARS, config.DEFAULT_LIMIT, config.MAX_LIMIT) == (200, 10, 50)
    assert (config.CLIENT_TYPO_SIMILARITY, config.NAME_WEIGHT, config.EMAIL_WEIGHT) == (0.6, 1.0, 0.7)
    assert config.DESCRIPTION_WEIGHT == 0.5
    assert (config.EXACT_SCORE_MIN, config.FUZZY_SCORE_MAX) == (0.5, 0.49)
    limits = (config.MAX_NAME_CHARS, config.MAX_EMAIL_CHARS, config.MAX_DESCRIPTION_CHARS)
    assert limits == (100, 254, 2000)
    assert (config.MAX_SOCIAL_LINKS, config.MAX_SOCIAL_LINK_CHARS) == (20, 2048)
    assert (config.SCORE_DECIMALS, config.RETRY_AFTER_SECONDS) == (4, 5)
    assert (config.EMBEDDING_DIM, config.FTS_CONFIG) == (768, 'english')
    # every exact match ranks above every typo match, also after rounding
    assert round(config.FUZZY_SCORE_MAX, config.SCORE_DECIMALS) < config.EXACT_SCORE_MIN


def test_services_is_a_frozen_bundle_of_four() -> None:
    settings = Settings(database_url='postgresql://u:p@db:5432/nevis')
    services = Services(settings=settings, engine=cast(Engine, None), embedder=None, concepts=None)

    assert [field.name for field in dataclasses.fields(Services)] == [
        'settings',
        'engine',
        'embedder',
        'concepts',
    ]
    with pytest.raises(dataclasses.FrozenInstanceError):
        services.embedder = object()  # type: ignore[misc]
