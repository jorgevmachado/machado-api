from __future__ import annotations

import re
import unicodedata

STARTER_POKEMON_NAMES = {"bulbasaur", "charmander", "squirtle"}
DEFAULT_TRAINER_POKEBALLS = 1
DEFAULT_TRAINER_CAPTURE_RATE = 75


def resolve_effective_nickname(pokemon_name: str, nickname: str | None) -> str:
    normalized = (nickname or "").strip()
    return normalized or pokemon_name


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "pokemon"


def build_unique_owned_name(base_slug: str, existing_names: set[str]) -> str:
    if base_slug not in existing_names:
        return base_slug

    suffix = 2
    while f"{base_slug}-{suffix}" in existing_names:
        suffix += 1
    return f"{base_slug}-{suffix}"
