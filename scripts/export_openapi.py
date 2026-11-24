"""Write docs/openapi.json from the application's own schema:

    uv run python scripts/export_openapi.py

tests/unit/test_openapi.py fails when the committed file differs from the app, so run this after every API
change.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # run as a file: make the repository root importable

from app.main import create_app  # noqa: E402

TARGET = ROOT / 'docs' / 'openapi.json'


def main() -> None:
    TARGET.write_text(
        json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    print(f'wrote {TARGET.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
