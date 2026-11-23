"""Without the model: importing app.embedding switches telemetry and the model hub off before onnxruntime is
loaded; the self-check looks for the model where the service does and refuses vectors unlike the model's."""

import math
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import numpy as np
import pytest

from app import embedding
from app.config import Settings
from app.embedding import DIM, GOLDEN_COSINE, SelfCheckError, Vector

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = ('ORT_DISABLE_TELEMETRY', 'HF_HUB_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY')


def vector(length: int, *values: float) -> Vector:
    """`values` first, zeros after them."""
    result = np.zeros(length, dtype=np.float32)
    result[: len(values)] = values
    return result


AXIS = vector(DIM, 1.0)
AT_GOLDEN_COSINE = vector(DIM, GOLDEN_COSINE, math.sqrt(1 - GOLDEN_COSINE**2))  # unit length


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


@pytest.mark.parametrize('model_dir', [None, '/srv/models/leaf-ir'])
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
        (vector(DIM - 1, 1.0), AT_GOLDEN_COSINE, 'dimension'),
        (2 * AXIS, AT_GOLDEN_COSINE, 'norms'),
        (np.full(DIM, np.nan, dtype=np.float32), AT_GOLDEN_COSINE, 'norms'),
        (AXIS, vector(DIM, 0.0, 1.0), 'cosine'),
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


def test_without_selfcheck_the_command_prints_its_usage_and_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """Without the flag nothing is checked, so an image build that forgot it must fail."""
    assert embedding.main([]) == 2

    output = capsys.readouterr()
    assert output.out == ''
    assert '--selfcheck' in output.err
