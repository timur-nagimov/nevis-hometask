"""The chunker: what each embedded text holds, and where a long document is cut."""

import pytest

from app.config import SELFCHECK_PASSAGE
from app.ingest import chunk_document


def words(n: int, word: str = 'word') -> str:
    return ' '.join([word] * n)


def body(text: str) -> str:
    """The chunk without its title line."""
    title, newline, rest = text.partition('\n')
    assert (title, newline) == ('T', '\n')
    return rest


def test_content_of_at_most_200_words_is_one_verbatim_chunk() -> None:
    content = '  Line one.\n\n\tLine two   with  spaces.  '
    assert chunk_document('T', content) == ['T\n' + content]
    at_the_limit = f' {words(150)}\n\n{words(50)}\n'  # 200 words: still as written, blank line and all
    assert chunk_document('T', at_the_limit) == ['T\n' + at_the_limit]


def test_paragraphs_are_packed_up_to_200_words_and_joined_by_a_blank_line() -> None:
    p1, p2, p3, p4 = words(80, 'alpha'), words(80, 'beta'), words(80, 'gamma'), words(80, 'delta')
    chunks = chunk_document('T', f'{p1}\n\n{p2}\n \n{p3}\n\n{p4}')
    assert chunks == [f'T\n{p1}\n\n{p2}', f'T\n{p3}\n\n{p4}']


def test_a_chunk_is_filled_up_to_exactly_200_words() -> None:
    p1, p2 = words(120, 'alpha'), words(80, 'beta')
    assert chunk_document('T', f'{p1}\n\n{p2}\n\ngamma') == [f'T\n{p1}\n\n{p2}', 'T\ngamma']


def test_a_paragraph_of_at_most_200_words_is_kept_as_written() -> None:
    paragraph = words(100, 'alpha') + '.\n' + words(100, 'beta')  # 200 words, a line break inside
    chunks = chunk_document('T', f'{words(250)}\n\n{paragraph}')
    assert chunks[-1] == f'T\n{paragraph}'


def test_whitespace_around_paragraphs_is_dropped() -> None:
    p1, p2 = words(150, 'alpha'), words(150, 'beta')
    assert chunk_document('T', f'\n\n  {p1} \n\n\t{p2}\n\n') == [f'T\n{p1}', f'T\n{p2}']


@pytest.mark.parametrize('mark', ['.', '!', '?'])
def test_a_long_paragraph_is_split_at_sentence_ends(mark: str) -> None:
    sentence = words(30, 'money') + mark  # six whole sentences fill 180 of a chunk's 200 words
    chunks = chunk_document('T', ' '.join([sentence] * 10))  # one paragraph of 300 words
    assert chunks == ['T\n' + ' '.join([sentence] * 6), 'T\n' + ' '.join([sentence] * 4)]


@pytest.mark.parametrize('mark', [';', ':'])
def test_semicolons_and_colons_also_end_a_sentence(mark: str) -> None:
    clause = words(30, 'item') + mark
    chunks = chunk_document('T', ' '.join([clause] * 9))  # one paragraph of 270 words, no full stop
    assert chunks == ['T\n' + ' '.join([clause] * 6), 'T\n' + ' '.join([clause] * 3)]


def test_a_sentence_over_200_words_is_cut_at_word_boundaries() -> None:
    chunks = chunk_document('T', words(450, 'data'))
    assert chunks == ['T\n' + words(200, 'data'), 'T\n' + words(200, 'data'), 'T\n' + words(50, 'data')]


def test_every_word_lands_in_exactly_one_chunk_in_text_order() -> None:
    content = '\n\n'.join(
        [
            'Opening note. ' + words(300, 'data'),  # a short sentence, then one of 300 words
            words(150, 'alpha'),
            words(60, 'beta') + '. ' + words(90, 'gamma') + '.',
        ]
    )
    chunks = chunk_document('T', content)
    assert [word for chunk in chunks for word in body(chunk).split()] == content.split()


def test_the_text_to_embed_is_title_newline_chunk() -> None:
    assert chunk_document('Utility bill', 'British Gas bill.') == ['Utility bill\nBritish Gas bill.']


def test_the_model_selfcheck_embeds_a_document_the_way_uploads_are_embedded() -> None:
    title, _, content = SELFCHECK_PASSAGE.partition('\n')
    assert chunk_document(title, content) == [SELFCHECK_PASSAGE]
