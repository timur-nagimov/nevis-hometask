"""ClientCreate: unit tests, no database."""

import sys
import unicodedata

import pytest
from pydantic import ValidationError

from app.config import MAX_DESCRIPTION_CHARS, MAX_NAME_CHARS, MAX_SOCIAL_LINK_CHARS, MAX_SOCIAL_LINKS
from app.schemas import ClientCreate

JOHN = {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@neviswealth.com'}
# Every character of Unicode category Cc: the "control characters" that the API rejects.
CONTROL = [chr(c) for c in range(sys.maxunicode + 1) if unicodedata.category(chr(c)) == 'Cc']


def rejected(**fields: object) -> set[object]:
    """Validate JOHN updated with `fields`; return the top-level field of every error."""
    with pytest.raises(ValidationError) as info:
        ClientCreate.model_validate({**JOHN, **fields})
    return {error['loc'][0] for error in info.value.errors()}


def test_category_cc_is_exactly_the_ranges_in_the_patterns() -> None:
    assert [chr(c) for c in range(0x00, 0x20)] + [chr(c) for c in range(0x7F, 0xA0)] == CONTROL


def test_minimal_body_gets_empty_description_and_links() -> None:
    assert ClientCreate.model_validate(JOHN).model_dump() == {**JOHN, 'description': '', 'social_links': []}


def test_null_description_and_links_become_empty() -> None:
    body = ClientCreate.model_validate({**JOHN, 'description': None, 'social_links': None})
    assert (body.description, body.social_links) == ('', [])


@pytest.mark.parametrize('email', ['owner@example.invalid', 'qa@nevis.test', 'dev@app.local'])
def test_special_use_domains_are_accepted(email: str) -> None:
    assert ClientCreate.model_validate({**JOHN, 'email': email}).email == email


def test_email_is_trimmed_and_otherwise_kept_as_sent() -> None:
    body = ClientCreate.model_validate({**JOHN, 'email': '  John.Doe@NevisWealth.COM '})
    assert body.email == 'John.Doe@NevisWealth.COM'


@pytest.mark.parametrize(
    'email',
    [
        'john.doe',
        'john.doe@',
        '@neviswealth.com',
        'John Doe <john.doe@neviswealth.com>',
        'admin@localhost',
        'a' * 250 + '@x.com',
        '',
        123,
    ],
)
def test_invalid_email_is_rejected(email: object) -> None:
    assert rejected(email=email) == {'email'}


def test_names_are_trimmed() -> None:
    body = ClientCreate.model_validate({**JOHN, 'first_name': '  Mary ', 'last_name': '\tMajor\n'})
    assert (body.first_name, body.last_name) == ('Mary', 'Major')


@pytest.mark.parametrize('value', ['', '   ', '\u00a0', 'x' * (MAX_NAME_CHARS + 1), None, 123, ['John']])
def test_bad_first_name_is_rejected(value: object) -> None:
    assert rejected(first_name=value) == {'first_name'}


@pytest.mark.parametrize('char', CONTROL, ids=lambda c: f'U+{ord(c):04X}')
def test_control_character_inside_a_name_is_rejected(char: str) -> None:
    assert rejected(last_name=f'Do{char}e') == {'last_name'}


@pytest.mark.parametrize('char', ['\u200b', '\u200d', '\u00ad', '\ufeff'])  # category Cf
def test_format_characters_are_allowed(char: str) -> None:
    body = ClientCreate.model_validate({**JOHN, 'first_name': f'Zero{char}Width', 'description': f'a{char}b'})
    assert (body.first_name, body.description) == (f'Zero{char}Width', f'a{char}b')


@pytest.mark.parametrize('value', ['  ', 'Line one\nLine two\tTabbed', 'x' * MAX_DESCRIPTION_CHARS])
def test_description_is_stored_verbatim(value: str) -> None:
    assert ClientCreate.model_validate({**JOHN, 'description': value}).description == value


@pytest.mark.parametrize('char', [c for c in CONTROL if c not in '\t\n'], ids=lambda c: f'U+{ord(c):04X}')
def test_other_control_characters_in_description_are_rejected(char: str) -> None:
    assert rejected(description=f'a{char}b') == {'description'}


@pytest.mark.parametrize('value', ['x' * (MAX_DESCRIPTION_CHARS + 1), 12345, {'text': 'x'}])
def test_bad_description_is_rejected(value: object) -> None:
    assert rejected(description=value) == {'description'}


def test_social_links_are_trimmed_and_kept_in_order() -> None:
    links = [' https://www.linkedin.com/in/johndoe ', '@johndoe', '@johndoe']
    body = ClientCreate.model_validate({**JOHN, 'social_links': links})
    assert body.social_links == ['https://www.linkedin.com/in/johndoe', '@johndoe', '@johndoe']


@pytest.mark.parametrize(
    'links',
    [
        [''],
        ['   '],
        ['x' * (MAX_SOCIAL_LINK_CHARS + 1)],
        ['ok'] * (MAX_SOCIAL_LINKS + 1),
        ['a\nb'],
        [42],
        'https://x.example',
    ],
)
def test_bad_social_links_are_rejected(links: object) -> None:
    assert rejected(social_links=links) == {'social_links'}


def test_unknown_members_are_ignored() -> None:
    body = ClientCreate.model_validate({**JOHN, 'id': '123', 'created_at': 'yesterday'})
    assert set(body.model_dump()) == {'first_name', 'last_name', 'email', 'description', 'social_links'}


def test_longest_values_are_accepted() -> None:
    links = ['x' * MAX_SOCIAL_LINK_CHARS] * MAX_SOCIAL_LINKS
    body = ClientCreate.model_validate({**JOHN, 'first_name': 'x' * MAX_NAME_CHARS, 'social_links': links})
    assert (len(body.first_name), len(body.social_links)) == (MAX_NAME_CHARS, MAX_SOCIAL_LINKS)
