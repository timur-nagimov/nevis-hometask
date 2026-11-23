"""scripts/fetch_model.py: download URL and headers, sha256 and size check, retries and their waits, every
listed file, usage, the app's model; no network (urlopen is replaced)."""

import hashlib
import importlib.util
import io
import urllib.error
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


def test_fetch_rejects_a_file_of_another_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The size is checked on its own: here the checksum matches."""
    script = load_script(monkeypatch, None)
    data = b'model bytes'
    monkeypatch.setattr(script.urllib.request, 'urlopen', lambda request, timeout: io.BytesIO(data))
    monkeypatch.setattr(script.time, 'sleep', lambda seconds: None)

    with pytest.raises(SystemExit, match='size mismatch'):
        script.fetch('tokenizer.json', hashlib.sha256(data).hexdigest(), len(data) + 1, tmp_path, attempts=2)


def test_the_waits_between_attempts_double_up_to_a_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = load_script(monkeypatch, None)
    waits: list[float] = []

    def refused(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        raise urllib.error.URLError('connection refused')

    monkeypatch.setattr(script.urllib.request, 'urlopen', refused)
    monkeypatch.setattr(script.time, 'sleep', waits.append)

    with pytest.raises(SystemExit, match='could not download'):
        script.fetch('tokenizer.json', '0' * 64, 1, tmp_path, attempts=6)

    assert waits == [2, 4, 8, 16, script.MAX_WAIT_SECONDS]  # five waits for six attempts


def test_a_token_in_the_environment_is_not_sent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The model is public; the build sends no credentials, whatever its environment holds."""
    monkeypatch.setenv('HF_TOKEN', 'hf_not_a_real_token')
    script = load_script(monkeypatch, None)
    data = b'model bytes'
    headers: list[dict[str, str]] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        headers.append(dict(request.header_items()))
        return io.BytesIO(data)

    monkeypatch.setattr(script.urllib.request, 'urlopen', fake_urlopen)
    script.fetch('tokenizer.json', hashlib.sha256(data).hexdigest(), len(data), tmp_path)

    assert headers == [{'User-agent': script.USER_AGENT}]


def test_main_downloads_every_listed_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = load_script(monkeypatch, None)
    contents = {'onnx/first.onnx': b'first file', 'second.json': b'second file'}
    files = {rel: (hashlib.sha256(data).hexdigest(), len(data)) for rel, data in contents.items()}
    monkeypatch.setattr(script, 'FILES', files)
    base = f'https://huggingface.co/MongoDB/mdbr-leaf-ir/resolve/{script.REVISION}/'

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> io.BytesIO:
        return io.BytesIO(contents[request.full_url.removeprefix(base)])

    monkeypatch.setattr(script.urllib.request, 'urlopen', fake_urlopen)
    script.main([str(tmp_path)])

    assert {rel: (tmp_path / rel).read_bytes() for rel in contents} == contents
    *ok_lines, total = capsys.readouterr().out.splitlines()
    assert [line.split()[:2] for line in ok_lines] == [['ok', rel] for rel in contents]
    assert total.startswith('total ')


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
