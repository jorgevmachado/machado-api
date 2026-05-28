from pydantic import BaseModel

from app.shared.utils.string import (
    TextLanguageSchema,
    _normalize_entry,
    get_text_language,
    is_valid_uuid,
)


class TestStringIsValidUuid:
    @staticmethod
    def test_is_valid_uuid_valid():
        assert is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")

    @staticmethod
    def test_is_valid_uuid_invalid():
        assert not is_valid_uuid("invalid-uuid")

    @staticmethod
    def test_is_valid_uuid_none():
        assert not is_valid_uuid(None)


class TestNormalizeEntry:
    @staticmethod
    def test_normalize_entry_with_dict():
        entry = {"key": "value"}
        result = _normalize_entry(entry)
        assert result == {"key": "value"}

    @staticmethod
    def test_normalize_entry_with_basemodel():
        class TestModel(BaseModel):
            key: str

        entry = TestModel(key="value")
        result = _normalize_entry(entry)
        assert result == {"key": "value"}

    @staticmethod
    def test_normalize_entry_with_other():
        entry = type(
            "TestType", (), {"__iter__": lambda self: iter([("key", "value")])}
        )()
        result = _normalize_entry(entry)
        assert result == {"key": "value"}


class TestGetTextLanguage:
    @staticmethod
    def test_get_text_language_with_group():
        entries = [
            {
                "language": {"name": "en"},
                "version_group": {"name": "generation-i"},
                "flavor_text": "Example text",
            },
        ]
        result = get_text_language(
            entries,
            "flavor_text",
            group="generation-i",
            language="en",
        )
        assert isinstance(result, TextLanguageSchema)
        assert result.text == "Example text"
        assert not result.error

    @staticmethod
    def test_get_text_language_without_group():
        entries = [
            {
                "language": {"name": "en"},
                "flavor_text": "Example text",
            },
        ]
        result = get_text_language(entries, "flavor_text", language="en")
        assert isinstance(result, TextLanguageSchema)
        assert result.text == "Example text"

    @staticmethod
    def test_get_text_language_with_subtext():
        entries = [
            {
                "language": {"name": "en"},
                "flavor_text": "Example text",
                "description": "Example description",
            },
        ]
        result = get_text_language(
            entries,
            "flavor_text",
            subtitle="description",
            language="en",
        )
        assert result.text == "Example text"
        assert result.subtext == "Example description"

    @staticmethod
    def test_get_text_language_empty_entries():
        result = get_text_language([], "flavor_text", language="en")
        assert result.error
        assert result.text == ""

    @staticmethod
    def test_get_text_language_missing_key():
        entries = [
            {
                "language": {"name": "en"},
            },
        ]
        result = get_text_language(entries, "flavor_text", language="en")
        assert result.error
        assert result.text == ""
