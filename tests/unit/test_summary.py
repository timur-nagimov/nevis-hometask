"""The lead summary: first sentences within 300 characters, plus an ellipsis when truncated."""

import pytest

from app.ingest import lead_summary


def test_short_content_is_its_own_summary_with_whitespace_collapsed() -> None:
    content = '  British Gas\tbill.\n\n  Amount  due\n£84.20.\n'
    assert lead_summary(content) == 'British Gas bill. Amount due £84.20.'


@pytest.mark.parametrize('mark', ['.', '!', '?'])
def test_whole_sentences_are_taken_while_they_fit_in_300_characters(mark: str) -> None:
    s1, s2, s3 = 'A' * 99 + mark, 'B' * 99 + mark, 'C' * 120 + mark  # 100 + 1 + 100 = 201; +1 +121 = 323
    assert lead_summary(f'{s1} {s2} {s3}') == f'{s1} {s2}'
    s4 = 'D' * 97 + mark  # 201 + 1 + 98 = 300: fits exactly
    assert lead_summary(f'{s1} {s2} {s4} {s3}') == f'{s1} {s2} {s4}'
    s5 = 'D' * 98 + mark  # 201 + 1 + 99 = 301: one character too many
    assert lead_summary(f'{s1} {s2} {s5}') == f'{s1} {s2}'


def test_no_sentence_is_skipped_to_fill_the_summary() -> None:
    s1, s2, s3 = 'A' * 99 + '.', 'B' * 249 + '.', 'C' * 9 + '.'  # 100 + 1 + 250 = 351: s2 does not fit
    assert lead_summary(f'{s1} {s2} {s3}') == s1


def test_an_overlong_first_sentence_is_cut_at_a_word_boundary_with_an_ellipsis() -> None:
    sentence = ' '.join(f'word{i}' for i in range(100)) + '.'  # 690 characters, one sentence
    summary = lead_summary(sentence)
    kept = summary.removesuffix('…')
    assert summary.endswith('…') and len(kept) <= 300
    assert sentence.startswith(kept) and sentence[len(kept)] == ' '


def test_a_first_sentence_is_cut_only_when_it_is_over_300_characters() -> None:
    sentence = ' '.join(['word'] * 60) + '.'
    assert len(sentence) == 300
    assert lead_summary(sentence) == sentence
    assert lead_summary('x' + sentence) == 'x' + ' '.join(['word'] * 59) + '…'


def test_a_first_sentence_without_a_space_is_cut_at_300_characters() -> None:
    assert lead_summary('x' * 400 + '. Next sentence.') == 'x' * 300 + '…'


@pytest.mark.parametrize('mark', [',', ';', ':'])
def test_a_comma_semicolon_or_colon_before_the_cut_is_dropped(mark: str) -> None:
    sentence = f'{mark} '.join(f'item{i}' for i in range(80)) + '.'  # 629 characters, one sentence
    summary = lead_summary(sentence)
    assert summary.endswith('…') and not summary.removesuffix('…').endswith(mark)
