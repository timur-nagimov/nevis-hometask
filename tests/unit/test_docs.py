"""The documents quote only what the repository prints.

- the quality cells of README.md and eval/README.md are cells of eval/results/ (eval/run_testset.py's output);
- docs/SEARCH.md's cosine table is eval/results/cosines.md (the output of eval/cosine_table.py);
- the README's transcripts are copied from docs/demo-transcript.txt (the output of scripts/demo.sh);
- relative links in README.md, every docs/*.md and eval/README.md resolve;
- the README says how to run, reset and test, and what the first build downloads.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'eval' / 'results'
LINK = re.compile(r'\]\(([^)#\s]+)')  # the target of a Markdown link, without its #anchor
FENCE = re.compile(r'^```.*?^```', re.S | re.M)  # a fenced code block


def _readme() -> str:
    return (ROOT / 'README.md').read_text(encoding='utf-8')


def _between(text: str, name: str) -> str:
    start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    assert start in text and end in text, f'missing markers {start} and {end}'
    return text.split(start, 1)[1].split(end, 1)[0]


def _table_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith('|')]


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip('|').split('|')]


def _runner_cells(name: str) -> set[str]:
    """Every value cell of the tables that the evaluation runner printed into eval/results/<name>."""
    text = (RESULTS / name).read_text(encoding='utf-8')
    cells: set[str] = set()
    for row in _table_lines(text):
        label, *values = _cells(row)
        if label and label != '---':  # a row of values, not a header or a separator
            cells.update(values)
    return cells


@pytest.mark.parametrize(
    'path',
    [ROOT / 'README.md', *sorted((ROOT / 'docs').glob('*.md')), ROOT / 'eval' / 'README.md'],
    ids=lambda path: str(path.relative_to(ROOT)),
)
def test_relative_links_resolve(path: Path) -> None:
    for target in LINK.findall(FENCE.sub('', path.read_text(encoding='utf-8'))):
        if '://' not in target:
            assert (path.parent / target).exists(), f'{path.relative_to(ROOT)}: broken link {target}'


@pytest.mark.parametrize(('doc', 'min_rows'), [('README.md', 3), ('eval/README.md', 6)])
def test_quality_cells_are_runner_output(doc: str, min_rows: int) -> None:
    with_concepts = _runner_cells('with-concepts.txt')
    no_concepts = _runner_cells('no-concepts.txt')
    text = (ROOT / doc).read_text(encoding='utf-8')
    rows = _table_lines(_between(text, 'quality'))[2:]  # after the header and its separator
    assert len(rows) >= min_rows, f'the quality table of {doc} needs at least {min_rows} rows'
    for row in rows:
        label, with_map, without_map = _cells(row)
        assert with_map in with_concepts, f'{label}: {with_map!r} is not in eval/results/with-concepts.txt'
        assert without_map in no_concepts, f'{label}: {without_map!r} is not in eval/results/no-concepts.txt'


def test_cosine_table_is_the_script_output() -> None:
    expected = _table_lines((RESULTS / 'cosines.md').read_text(encoding='utf-8'))
    text = (ROOT / 'docs' / 'SEARCH.md').read_text(encoding='utf-8')
    assert expected and _table_lines(_between(text, 'cosines')) == expected


def test_transcripts_are_captured_output() -> None:
    transcript = (ROOT / 'docs' / 'demo-transcript.txt').read_text(encoding='utf-8')
    pattern = r'<!-- transcript:start -->\s*```console\n(.*?)```\s*<!-- transcript:end -->'
    blocks = re.findall(pattern, _readme(), re.S)
    assert len(blocks) == 3, 'README needs three transcripts: NevisWealth, address proof, a junk query'
    for block in blocks:
        assert block.strip() in transcript, block.splitlines()[0]


@pytest.mark.parametrize(
    'fact',
    [
        'docker compose up --build -d',
        'scripts/demo.sh',
        'docker compose --profile test run --rm --no-deps tests',
        'docker compose down -v',
        'API_PORT',
        'cdn.jsdelivr.net',
        'docs/openapi.json',
        'docker.io',
        'ghcr.io',
        'PyPI',
        'huggingface.co',
    ],
)
def test_readme_states(fact: str) -> None:
    assert fact in _readme()
