"""scripts/fetch_model.py: download URL, sha256 check, retries, usage, the app's model; no network (urlopen is
replaced)."""

import hashlib
import importlib.util
import io
import urllib.request
from pathlib import Path
from types import ModuleType

import pytest

from app import config

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'fetch_model.py'


def load_script(monkeypatch: pytest.MonkeyPatch, endpoint: str | None) -> ModuleType:
    """A fresh copy of the script: it reads HF_ENDPOINT when it is loaded."""
    if endpoint is None:
        monkeypatch.delenv('HF_ENDPOINT', raising=False)
    else:
        monkeypatch.setenv('HF_ENDPOINT', endpoint)
    spec = importlib.util.spec_from_file_location('fetch_model', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_endpoint_defaults_to_hugging_face_and_accepts_a_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    assert load_script(monkeypatch, None).ENDPOINT == 'https://huggingface.co'
    assert load_script(monkeypatch, '').ENDPOINT == 'https://huggingface.co'
    assert load_script(monkeypatch, 'https://mirror.example/').ENDPOINT == 'https://mirror.example'


def test_fetch_writes_a_verified_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = load_script(monkeypatch, None)
    data = b'model bytes'
    urls: list[str] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        urls.append(request.full_url)
        return io.BytesIO(data)

    monkeypatch.setattr(script.urllib.request, 'urlopen', fake_urlopen)
    script.fetch('onnx/model.onnx', hashlib.sha256(data).hexdigest(), len(data), tmp_path)

    assert (tmp_path / 'onnx' / 'model.onnx').read_bytes() == data
    assert urls == [f'https://huggingface.co/MongoDB/mdbr-leaf-ir/resolve/{script.REVISION}/onnx/model.onnx']


def test_fetch_gives_up_after_checksum_mismatches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = load_script(monkeypatch, None)
    corrupt = b'corrupt'
    urls: list[str] = []

    def corrupt_urlopen(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        urls.append(request.full_url)
        return io.BytesIO(corrupt)

    monkeypatch.setattr(script.urllib.request, 'urlopen', corrupt_urlopen)
    monkeypatch.setattr(script.time, 'sleep', lambda seconds: None)

    with pytest.raises(SystemExit, match='could not download'):
        script.fetch('tokenizer.json', '0' * 64, len(corrupt), tmp_path, attempts=2)
    assert len(urls) == 2


def test_without_a_target_directory_the_script_prints_its_usage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script = load_script(monkeypatch, None)

    with pytest.raises(SystemExit) as stop:
        script.main([])

    assert stop.value.code == 2
    assert 'target-dir' in capsys.readouterr().err


def test_the_app_and_the_script_pin_the_same_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """The script cannot import the app, so the pinned model is written twice."""
    script = load_script(monkeypatch, None)

    assert (script.REPO, script.REVISION) == (config.MODEL_REPO, config.MODEL_REVISION)
    assert {config.MODEL_FILE, config.TOKENIZER_FILE} <= script.FILES.keys()  # the files the embedder opens
