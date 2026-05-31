from __future__ import annotations

import re
import unicodedata
import random
from math import floor

def resolve_effective_nickname(pokemon_name: str, nickname: str | None) -> str:
    normalized = (nickname or "").strip()
    return normalized or pokemon_name


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "pokemon"


def build_unique_owned_name(base_slug: str, existing_pokemons: set[str]) -> str:
    if base_slug not in existing_pokemons:
        return base_slug

    suffix = 2
    while f"{base_slug}-{suffix}" in existing_pokemons:
        suffix += 1
    return f"{base_slug}-{suffix}"

def calculate_capture_chance_percent(
        pokedex_hp: int,
        pokedex_max_hp: int,
        trainer_capture_rate: int,
        pokemon_capture_rate: int
) -> int:
    safe_max_hp = max(pokedex_max_hp, 1)
    hp_factor = 1 - (pokedex_hp / safe_max_hp)
    rate_advantage = max(0.0, (trainer_capture_rate - pokemon_capture_rate) / 255)
    chance = 15 + (hp_factor * 55) + (rate_advantage * 25)
    return max(15, min(95, floor(chance)))

def rolled_capture_success(chance_percent: int) -> bool:
    return random.randint(1, 100) <= chance_percent