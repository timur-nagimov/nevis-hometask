"""The packaged concept map is the default of NEVIS_CONCEPTS_FILE."""

from pathlib import Path

from app.config import PACKAGED_CONCEPTS_FILE, Settings


def test_the_default_concept_map_is_the_packaged_file() -> None:
    settings = Settings(database_url='postgresql://nevis@localhost/nevis')

    assert settings.concepts_file == PACKAGED_CONCEPTS_FILE
    assert Path(PACKAGED_CONCEPTS_FILE).parts[-3:] == ('app', 'data', 'concepts.yaml')
