from __future__ import annotations

import random
import re
import unicodedata
from math import floor

from app.models.pokemon import Pokemon
from app.models.pokemon_move import PokemonMove

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


def build_initial_attributes(base_pokemon: Pokemon) -> dict[str, int]:
    attack = _rolled_stat(base_pokemon.attack)
    defense = _rolled_stat(base_pokemon.defense)
    speed = _rolled_stat(base_pokemon.speed)
    special_attack = _rolled_stat(base_pokemon.special_attack)
    special_defense = _rolled_stat(base_pokemon.special_defense)
    max_hp = _rolled_hp(base_pokemon.hp)

    return {
        "level": 1,
        "experience": 0,
        "hp": max_hp,
        "max_hp": max_hp,
        "attack": attack,
        "defense": defense,
        "special_attack": special_attack,
        "special_defense": special_defense,
        "speed": speed,
    }


def select_initial_moves(moves: list[PokemonMove]) -> list[PokemonMove]:
    unique_moves: list[PokemonMove] = []
    seen_names: set[str] = set()

    for move in moves:
        if move.deleted_at is not None or move.name in seen_names:
            continue
        seen_names.add(move.name)
        unique_moves.append(move)

    if len(unique_moves) <= 4:
        return unique_moves

    return random.sample(unique_moves, 4)


def _rolled_stat(base_value: int | None) -> int:
    value = max(base_value or 0, 1)
    return max(1, floor(value * random.uniform(0.90, 1.10)))


def _rolled_hp(base_value: int | None) -> int:
    value = max(base_value or 0, 1)
    return max(10, floor(value * random.uniform(0.95, 1.15)) + 5)
