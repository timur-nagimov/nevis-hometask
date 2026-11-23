"""Every unit test starts without the caller's NEVIS_* variables, including settings added later."""

import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(f'NEVIS_{name.upper()}', raising=False)
