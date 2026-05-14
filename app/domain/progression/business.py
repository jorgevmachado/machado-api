from __future__ import annotations

import random
from math import floor

from app.models.pokemon import Pokemon


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


def _rolled_stat(base_value: int | None) -> int:
    value = max(base_value or 0, 1)
    return max(1, floor(value * random.uniform(0.90, 1.10)))


def _rolled_hp(base_value: int | None) -> int:
    value = max(base_value or 0, 1)
    return max(10, floor(value * random.uniform(0.95, 1.15)) + 5)
