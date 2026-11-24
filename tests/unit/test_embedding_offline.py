"""Without the model: importing app.embedding switches telemetry and the model hub off before onnxruntime is
loaded; the self-check looks for the model where the service does and refuses vectors unlike the model's;
the command's exit status, which is what stops the image build."""

import math
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import numpy as np
import pytest

from app import embedding
from app.config import EMBEDDING_DIM, GOLDEN_COSINE, MODEL_FILE, TOKENIZER_FILE, Settings
from app.embedding import SelfCheckError, Vector

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = ('ORT_DISABLE_TELEMETRY', 'HF_HUB_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY')


def vector(length: int, *values: float) -> Vector:
    """`values` first, zeros after them."""
    result = np.zeros(length, dtype=np.float32)
    result[: len(values)] = values
    return result


AXIS = vector(EMBEDDING_DIM, 1.0)
AT_GOLDEN_COSINE = vector(EMBEDDING_DIM, GOLDEN_COSINE, math.sqrt(1 - GOLDEN_COSINE**2))  # unit length


class FixedVectors:
    """Stands in for the model: the self-check's query and passage get these vectors."""

    def __init__(self, query: Vector, passage: Vector) -> None:
        self._query = query
        self._passage = passage

    def embed_query(self, text: str) -> Vector:
        return self._query

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        return [self._passage]


def test_the_import_sets_the_variables_and_leaves_onnxruntime_unloaded() -> None:
    # a fresh interpreter: this one may have loaded onnxruntime already
    script = (
        'import os, sys, app.embedding; '
        f'print(*[os.environ.get(name) for name in {VARIABLES!r}], "onnxruntime" in sys.modules)'
    )
    environment = {name: value for name, value in os.environ.items() if name not in VARIABLES}

    result = subprocess.run(
        [sys.executable, '-c', script], cwd=ROOT, env=environment, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ['1', '1', '1', 'False']


class ModelOpened(Exception):
    """Ends the self-check once it has chosen the model directory."""


@pytest.mark.parametrize('model_dir', [None, '/srv/models/leaf-ir', ''], ids=['unset', 'set', 'empty'])
def test_the_selfcheck_opens_the_model_directory_of_the_service(
    monkeypatch: pytest.MonkeyPatch, model_dir: str | None
) -> None:
    if model_dir is not None:
        monkeypatch.setenv('NEVIS_MODEL_DIR', model_dir)
    opened: list[Path] = []

    def open_model(path: Path, threads: int) -> NoReturn:
        opened.append(path)
        raise ModelOpened

    monkeypatch.setattr(embedding, 'Embedder', open_model)

    with pytest.raises(ModelOpened):
        embedding.selfcheck()

    assert opened == [Path(Settings(database_url='postgresql://u:p@db:5432/nevis').model_dir)]


@pytest.mark.parametrize(
    ('query', 'passage', 'error'),
    [
        (vector(EMBEDDING_DIM - 1, 1.0), AT_GOLDEN_COSINE, 'dimension'),
        (2 * AXIS, AT_GOLDEN_COSINE, 'norms'),
        (np.full(EMBEDDING_DIM, np.nan, dtype=np.float32), AT_GOLDEN_COSINE, 'norms'),
        (AXIS, vector(EMBEDDING_DIM, 0.0, 1.0), 'cosine'),
    ],
    ids=['dimension', 'length', 'nan', 'cosine'],
)
def test_the_selfcheck_refuses_vectors_unlike_the_pinned_model(
    monkeypatch: pytest.MonkeyPatch, query: Vector, passage: Vector, error: str
) -> None:
    monkeypatch.setattr(embedding, 'Embedder', lambda path, threads: FixedVectors(query, passage))

    with pytest.raises(SelfCheckError, match=error):
        embedding.selfcheck('/models')


def test_the_selfcheck_returns_the_cosine_it_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding, 'Embedder', lambda path, threads: FixedVectors(AXIS, AT_GOLDEN_COSINE))

    assert embedding.selfcheck('/models') == pytest.approx(GOLDEN_COSINE)


def run_command(*arguments: str) -> subprocess.CompletedProcess[str]:
    """`python -m app.embedding ...` in a new process, the way the image build runs it."""
    return subprocess.run(
        [sys.executable, '-m', 'app.embedding', *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_without_selfcheck_the_command_prints_its_usage_and_fails() -> None:
    """Without the flag nothing is checked, so an image build that forgot it must fail."""
    result = run_command()

    assert result.returncode == 2
    assert result.stdout == ''
    assert '--selfcheck' in result.stderr


def test_a_directory_without_the_model_fails_the_selfcheck_in_one_line(tmp_path: Path) -> None:
    """A wrong --model-dir or NEVIS_MODEL_DIR: exit status 1 stops the build, and the line names the cause."""
    result = run_command('--selfcheck', '--model-dir', str(tmp_path))

    assert result.returncode == 1
    assert result.stdout == ''
    assert result.stderr.splitlines() == [
        f'selfcheck FAILED: {tmp_path}: model files not found or not readable: {MODEL_FILE}, {TOKENIZER_FILE}'
    ]
