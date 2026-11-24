"""eval.metrics on tiny hand-made suites and results: the first-10 metrics, the strict pass, the report."""

from typing import Any

import pytest

from eval.metrics import FirstTen, Scoreboard, Tally, group_of, kinds_of, render, strict_failures

KINDS = {'c1': 'client', 'c2': 'client'} | {f'd{i}': 'document' for i in range(1, 16)}


def test_relevant_is_right_acceptable_is_ignored_anything_else_is_wrong() -> None:
    m = FirstTen()
    m.add({'relevant': ['d1', 'd2'], 'acceptable': ['d3']}, ['d1', 'd3', 'd9'], KINDS)
    assert (m.tp, m.fp, m.fn, m.pos_n, m.pos_hit) == (1, 1, 1, 1, 1)
    assert (m.precision, m.recall, m.f1) == (0.5, 0.5, 0.5)


def test_others_ignore_has_no_wrong_results() -> None:
    m = FirstTen()
    m.add({'relevant': ['d1'], 'others': 'ignore'}, ['d9', 'd1', 'd8'], KINDS)
    assert (m.tp, m.fp, m.fn) == (1, 0, 0)


def test_a_no_answer_query_is_clean_only_when_nothing_comes_back() -> None:
    m = FirstTen()
    m.add({'empty': True}, [], KINDS)
    m.add({'empty': True}, ['c1', 'd1'], KINDS)
    assert (m.neg_n, m.neg_clean, m.fp, m.pos_n) == (2, 1, 2, 0)
    assert m.clean == 0.5


def test_the_scope_filter_comes_before_the_cut_at_ten() -> None:
    returned = ['c1', 'c2', *(f'd{i}' for i in range(1, 12))]  # two clients, then d1 ... d11
    m = FirstTen()
    m.add({'scope': 'documents', 'relevant': ['d10', 'd11']}, returned, KINDS)
    assert (m.tp, m.fn, m.fp) == (1, 1, 9)  # without the clients d10 is 10th and d11 is 11th


def test_at_most_ten_misses_per_query() -> None:
    relevant = [f'd{i}' for i in range(1, 16)]
    m = FirstTen()
    m.add({'relevant': relevant}, relevant[:10], KINDS)
    assert (m.tp, m.fn, m.recall) == (10, 0, 1.0)


def test_a_query_with_neither_answer_nor_empty_is_not_counted() -> None:
    m = FirstTen()
    m.add({'relevant': [], 'acceptable': ['d1']}, ['d1', 'd2'], KINDS)
    assert m == FirstTen()


def test_no_counts_give_zero_instead_of_a_division_by_zero() -> None:
    m = FirstTen()
    assert (m.precision, m.recall, m.f1, m.hit_at_10, m.clean) == (0.0, 0.0, 0.0, 0.0, 0.0)


def test_strict_pass_is_score_py_with_the_api_limit_of_50() -> None:
    sixty = [f'd{i}' for i in range(60)]
    kinds = dict.fromkeys(sixty, 'document')
    assert strict_failures({'relevant': sixty}, sixty[:50], kinds) == []  # 50 of 60 are enough
    assert strict_failures({'relevant': sixty}, sixty[:49], kinds) == ['49 of 60 relevant returned, need 50']
    assert strict_failures({'relevant': ['d1']}, ['d1', 'd2'], kinds) == ["unexpected ['d2']"]
    assert strict_failures({'empty': True}, [], kinds) == []


@pytest.mark.parametrize(
    ('suite', 'group'),
    [
        ('codex-mixed', 'written blind (Codex, Claude)'),
        ('ds-fiqa', 'open datasets'),
        ('existing-clients-skeptic-44', 'research, independent of the design'),
        ('existing-clients-fixture-42', "research, written by the design's authors"),
    ],
)
def test_suites_are_grouped_by_origin(suite: str, group: str) -> None:
    assert group_of(suite) == group


def test_an_unknown_suite_has_no_group() -> None:
    with pytest.raises(ValueError, match='no origin group'):
        group_of('my-new-suite')


TINY: dict[str, Any] = {
    'suite': 'existing-documents-86',
    'corpus': {'clients': [{'id': 'c00'}], 'documents': [{'id': 'd1'}, {'id': 'd2'}]},
    'queries': [
        {
            'id': 'q1',
            'q': 'Address  Proof',
            'level': 'required',
            'split': 'dev',
            'scope': 'documents',
            'relevant': ['d1'],
        },
        {
            'id': 'q2',
            'q': 'chocolate cake',
            'level': 'expected',
            'split': 'test',
            'scope': 'documents',
            'empty': True,
        },
    ],
}


def test_corpus_ids_are_mapped_to_client_or_document() -> None:
    assert kinds_of(TINY) == {'c00': 'client', 'd1': 'document', 'd2': 'document'}


def test_scoreboard_counts_groups_levels_splits_and_examples() -> None:
    board = Scoreboard()
    tally, failed = board.add_suite(TINY, {'q1': ['d1'], 'q2': ['d2']})
    assert (tally.passed, tally.total) == (1, 2)
    assert [(query['id'], why) for query, why in failed] == [('q2', ["expected nothing, got ['d2']"])]
    assert {key: (t.passed, t.total) for key, t in board.strict.items()} == {
        'total': (1, 2),
        'research, independent of the design': (1, 2),
        'required': (1, 1),
        'expected': (0, 1),
        'existing-documents-86 dev': (1, 1),
        'existing-documents-86 test': (0, 1),
    }
    assert list(board.first_ten) == ['all suites', 'existing-documents-86 dev', 'existing-documents-86 test']
    assert board.examples['address proof'] == Tally(passed=1, total=1)  # 'Address  Proof'


def test_render_prints_the_three_tables() -> None:
    board = Scoreboard()
    board.add_suite(TINY, {'q1': ['d1'], 'q2': ['d2']})
    text = render(board, 'concept map on', ['existing-clients-skeptic-44/c_long (description)'])
    assert 'Skipped records (the API would reject them): existing-clients-skeptic-44/c_long' in text
    assert '| **total** | 1/2 (50 %) |' in text
    assert '| existing-documents-86 test | 0/1 (0 %) |' in text
    assert '| all suites | 0.50 | 1.00 | 0.667 | 1.00 | 0.00 (0/1) |' in text
    assert '| `address proof` | 1/1 |' in text
    assert '| `neviswealth` | 0/0 |' in text
