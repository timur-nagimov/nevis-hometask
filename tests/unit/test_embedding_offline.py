"""Importing app.embedding switches telemetry and the model hub off before onnxruntime is loaded."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = ('ORT_DISABLE_TELEMETRY', 'HF_HUB_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY')


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
