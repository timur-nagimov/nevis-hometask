"""Claude enrichment at upload. Nothing here calls Anthropic."""

import pytest

from app.config import Settings

DSN = 'postgresql://nevis@localhost/unused'


def test_llm_settings_are_off_by_default() -> None:
    settings = Settings(database_url=DSN)

    assert settings.llm_enabled is False
    assert settings.llm_model == 'claude-haiku-5-5'
    assert settings.llm_timeout_seconds == 10.0
    assert settings.anthropic_api_key is None


def test_the_key_is_read_without_the_nevis_prefix_and_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-not-real')

    settings = Settings(database_url=DSN)

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == 'sk-ant-test-not-real'
    assert 'sk-ant-test-not-real' not in repr(settings)
