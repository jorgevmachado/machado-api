from __future__ import annotations

import random
from math import floor

from app.domain.trainer.progression.schema import AttributesCalculatedSchema
from app.models import GrowthRate
from app.models.pokemon import Pokemon
from app.shared.utils.number import calculate_by_formula


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


def calculate_progression(
    hp: int,
    level: int,
    speed: int,
    attack: int,
    defense: int,
    max_hp: int,
    experience: int,
    special_attack: int,
    special_defense: int,
    opponent_level: int,
    opponent_fainted: bool,
    opponent_base_experience: int,
    growth_rate: GrowthRate | None = None,
) -> AttributesCalculatedSchema | None:
    if not growth_rate:
        return None

    level_up = False
    current_level = level
    current_experience = experience

    if opponent_fainted:
        xp_gained = _calculate_experience(
            level=opponent_level,
            base_experience=opponent_base_experience,
        )

        current_experience = experience + xp_gained

        new_level = _level_from_experience(
            level=level,
            formula=growth_rate.formula,
            experience=current_experience,
        )

        if new_level > current_level:
            level_up = True
            current_level = int(new_level)

    return _calculate_attributes(
        hp=hp,
        level=current_level,
        speed=speed,
        attack=attack,
        max_hp=max_hp,
        defense=defense,
        level_up=level_up,
        experience=current_experience,
        special_attack=special_attack,
        special_defense=special_defense,
    )


def _calculate_experience(
    level: int, base_experience: int, xp_multiplier: int = 7
) -> int:
    return base_experience * max(1, level // xp_multiplier)


def _level_from_experience(level: int, formula: str, experience: int) -> float:
    current_level = level
    while True:
        experience_for_next_level = calculate_by_formula(formula, current_level + 1)

        if experience_for_next_level > experience:
            return level

        current_level += 1


def _calculate_attributes(
    hp: int,
    level: int,
    speed: int,
    attack: int,
    max_hp: int,
    defense: int,
    level_up: bool,
    experience: int,
    special_attack: int,
    special_defense: int,
) -> AttributesCalculatedSchema:
    attributes = AttributesCalculatedSchema(
        hp=hp,
        level=level,
        speed=speed,
        attack=attack,
        max_hp=max_hp,
        defense=defense,
        level_up=level_up,
        experience=experience,
        special_attack=special_attack,
        special_defense=special_defense,
    )
    if level_up:
        attributes.hp = calculate_attribute(
            base=hp, level=level, progression_value=level + 10
        )
        attributes.max_hp = calculate_attribute(
            base=max_hp, level=level, progression_value=level + 10
        )
        attributes.speed = calculate_attribute(base=speed, level=level)
        attributes.attack = calculate_attribute(base=attack, level=level)
        attributes.defense = calculate_attribute(base=defense, level=level)
        attributes.special_attack = calculate_attribute(
            base=special_attack, level=level
        )
        attributes.special_defense = calculate_attribute(
            base=special_defense, level=level
        )

    return attributes


def calculate_attribute(base: int, level: int, progression_value: int = 5) -> int:
    return (2 * base * level) // 100 + progression_value
