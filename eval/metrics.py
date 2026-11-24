"""Scoring of the test set: the strict pass and the first-10 metrics.

Strict pass: every check of testset/score.py passes (testset/README.md, "Как засчитывается ответ") on
results asked for with the API's largest limit. The first-10 metrics look at the first 10 results after
the scope filter:

- micro precision / recall / F1 over (query, result) pairs: a relevant result is a true positive, an
  acceptable one is ignored, anything else is a false positive (only for queries with `others: wrong`, and
  every result of a no-answer query); a missed relevant result is a false negative (at most 10 per query);
- hit@10: the share of queries with an answer that have a relevant result in the first 10;
- no-answer clean: the share of no-answer queries (`empty: true`) that return nothing.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.config import MAX_LIMIT
from testset.score import checks

K = 10  # the first-10 metrics look at what the API returns by default
LEVELS = ('required', 'expected', 'nice')
GROUPS: list[tuple[str, Callable[[str], bool]]] = [
    ('written blind (Codex, Claude)', lambda n: n.startswith(('codex-', 'claude-'))),
    ('open datasets', lambda n: n.startswith('ds-')),
    (
        'research, independent of the design',
        lambda n: n in ('existing-clients-skeptic-44', 'existing-documents-86'),
    ),
    (
        "research, written by the design's authors",
        lambda n: n in ('existing-clients-fixture-42', 'tools-mini-6'),
    ),
]
EXAMPLES = ('neviswealth', 'address proof')  # the assignment's examples, case and spaces ignored

Failure = tuple[dict[str, Any], list[str]]  # (query, why it fails)


def group_of(suite_name: str) -> str:
    """The origin group of a suite."""
    for label, belongs in GROUPS:
        if belongs(suite_name):
            return label
    raise ValueError(f'suite {suite_name!r} belongs to no origin group; add it to GROUPS')


def kinds_of(suite: dict[str, Any]) -> dict[str, str]:
    """Suite id -> 'client' or 'document'."""
    corpus = suite['corpus']
    kinds = {c['id']: 'client' for c in corpus['clients']}
    kinds.update({d['id']: 'document' for d in corpus['documents']})
    return kinds


def strict_failures(query: dict[str, Any], returned: list[str], kinds: dict[str, str]) -> list[str]:
    """Why the query fails the strict pass; an empty list when it passes."""
    return checks(query, returned, kinds, MAX_LIMIT)


@dataclass
class Tally:
    passed: int = 0
    total: int = 0

    def add(self, ok: bool) -> None:
        self.passed += ok
        self.total += 1

    def cell(self) -> str:
        return f'{self.passed}/{self.total} ({100 * self.passed / self.total:.0f} %)'


@dataclass
class FirstTen:
    tp: int = 0  # relevant results in the first 10
    fp: int = 0  # wrong results in the first 10
    fn: int = 0  # relevant results missing from the first 10, at most 10 per query
    pos_n: int = 0  # queries with an answer
    pos_hit: int = 0  # ... that have a relevant result in the first 10
    neg_n: int = 0  # no-answer queries
    neg_clean: int = 0  # ... that return nothing

    def add(self, query: dict[str, Any], returned: list[str], kinds: dict[str, str]) -> None:
        scope = query.get('scope', 'all')
        got = [x for x in returned if scope == 'all' or kinds.get(x) == scope[:-1]][:K]
        rel, acc = set(query.get('relevant', [])), set(query.get('acceptable', []))
        if query.get('empty'):
            self.neg_n += 1
            self.neg_clean += not got
            self.fp += len(got)
            return
        if not rel:
            return
        tp = len(rel & set(got))
        self.tp += tp
        self.fn += min(len(rel), K) - tp
        if query.get('others', 'wrong') == 'wrong':
            self.fp += sum(1 for x in got if x not in rel and x not in acc)
        self.pos_n += 1
        self.pos_hit += tp > 0

    # Each ratio is 0.0 when it has nothing to count: a row of the report may have no queries of a kind.
    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    @property
    def hit_at_10(self) -> float:
        return self.pos_hit / self.pos_n if self.pos_n else 0.0

    @property
    def clean(self) -> float:
        return self.neg_clean / self.neg_n if self.neg_n else 0.0


@dataclass
class Scoreboard:
    """Totals over the suites scored so far."""

    strict: defaultdict[str, Tally] = field(default_factory=lambda: defaultdict(Tally))
    first_ten: defaultdict[str, FirstTen] = field(default_factory=lambda: defaultdict(FirstTen))
    examples: dict[str, Tally] = field(default_factory=lambda: {q: Tally() for q in EXAMPLES})

    def add_suite(self, suite: dict[str, Any], results: dict[str, list[str]]) -> tuple[Tally, list[Failure]]:
        """Score one suite's results ({query id: [suite ids, best first]}): its tally, its failures."""
        name = suite['suite']
        kinds = kinds_of(suite)
        group = group_of(name)
        tally = Tally()
        failed: list[Failure] = []
        for query in suite['queries']:
            returned = results[query['id']]
            reasons = strict_failures(query, returned, kinds)
            ok = not reasons
            tally.add(ok)
            if reasons:
                failed.append((query, reasons))
            splits = [f'{name} {query["split"]}'] if 'split' in query else []
            for key in ['total', group, query['level'], *splits]:
                self.strict[key].add(ok)
            for key in ['all suites', *splits]:
                self.first_ten[key].add(query, returned, kinds)
            normalised = ' '.join(query['q'].split()).casefold()
            if normalised in self.examples:
                self.examples[normalised].add(ok)
        return tally, failed


def render(board: Scoreboard, config: str, skipped: list[str]) -> str:
    """The report: strict pass, first-10 metrics and the two examples, as markdown tables."""
    fixed = ['total', *(label for label, _ in GROUPS), *LEVELS]
    splits = sorted(key for key in board.strict if key not in fixed)
    lines = [
        f'## Test set: {config}',
        '',
        'Skipped records (the API would reject them): ' + (', '.join(skipped) or 'none'),
        '',
        '### Strict pass (passed / total)',
        '',
        '| | passed |',
        '|---|---|',
    ]
    for key in [*fixed, *splits]:
        if key in board.strict:
            label = f'**{key}**' if key == 'total' else key
            lines.append(f'| {label} | {board.strict[key].cell()} |')
    lines += [
        '',
        '### First 10 results: micro precision / recall / F1, hit@10, no-answer queries clean',
        '',
        '| | precision | recall | F1 | hit@10 | no-answer clean |',
        '|---|---|---|---|---|---|',
    ]
    for key, m in board.first_ten.items():
        lines.append(
            f'| {key} | {m.precision:.2f} | {m.recall:.2f} | {m.f1:.3f} | {m.hit_at_10:.2f} '
            f'| {m.clean:.2f} ({m.neg_clean}/{m.neg_n}) |'
        )
    lines += [
        '',
        '### The assignment examples (strict pass, every suite that has the query)',
        '',
        '| | passed |',
        '|---|---|',
    ]
    for example, tally in board.examples.items():
        lines.append(f'| `{example}` | {tally.passed}/{tally.total} |')
    return '\n'.join(lines)
