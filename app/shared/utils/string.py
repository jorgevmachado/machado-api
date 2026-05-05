import uuid
from typing import Any, cast

from pydantic import BaseModel


def is_valid_uuid(value: str | None = None) -> bool:
    if not value:
        return False
    try:
        uuid_obj = uuid.UUID(value)
        return str(uuid_obj) == value
    except (ValueError, AttributeError, TypeError):
        return False


class TextLanguageSchema(BaseModel):
    text: str
    error: bool = False
    subtext: str | None = None
    language: str


def _normalize_entry(entry: Any) -> dict:
    if isinstance(entry, BaseModel):
        return entry.model_dump()
    if isinstance(entry, dict):
        return entry
    return dict(entry)


def get_text_language(
    entries: list[Any],
    title: str,
    group: str | None = None,
    subtitle: str | None = None,
    language: str = "en",
    group_title: str = "version_group",
) -> TextLanguageSchema:
    normalized = [_normalize_entry(e) for e in entries]

    if group is None:
        text_entry = next(
            (
                entry
                for entry in normalized
                if entry.get("language", {}).get("name") == language
            ),
            normalized[0] if normalized else None,
        )
    else:
        text_entry = next(
            (
                entry
                for entry in normalized
                if entry.get("language", {}).get("name") == language
                and entry.get(group_title, {}).get("name") == group
            ),
            normalized[0] if normalized else None,
        )

    if text_entry is None:
        return TextLanguageSchema(text="", error=True, language=language)

    if not text_entry.get(title):
        return TextLanguageSchema(text="", error=True, language=language)

    text: str = cast(str, text_entry.get(title))
    subtext_raw = text_entry.get(subtitle) if subtitle else None
    subtext: str | None = cast(str, subtext_raw) if subtext_raw else None

    return TextLanguageSchema(
        text=text,
        subtext=subtext,
        language=language,
    )
