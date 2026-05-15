from __future__ import annotations

import random
from collections.abc import Sequence

from fastapi import HTTPException
from http import HTTPStatus

from app.models import ExplorationEventTypeEnum, Pokemon, PokemonEncounter

MAX_PARTY_SIZE = 6
POKEBALL_REWARD_MIN = 1
POKEBALL_REWARD_MAX = 3
WILD_EVENT_THRESHOLD = 0.7


def resolve_initial_active_encounter(
    encounters: Sequence[PokemonEncounter],
) -> PokemonEncounter | None:
    if not encounters:
        return None
    return sorted(encounters, key=lambda encounter: encounter.order)[0]


def validate_party_selection(my_pokemon_ids: list) -> None:
    if len(my_pokemon_ids) > MAX_PARTY_SIZE:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Trainer party cannot exceed {MAX_PARTY_SIZE} Pokemon",
        )
    if len(set(my_pokemon_ids)) != len(my_pokemon_ids):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Trainer party cannot contain duplicate Pokemon",
        )


def choose_event_type() -> ExplorationEventTypeEnum:
    if random.random() < WILD_EVENT_THRESHOLD:
        return ExplorationEventTypeEnum.WILD_POKEMON
    return ExplorationEventTypeEnum.POKEBALLS


def choose_wild_pokemon(pokemons: Sequence[Pokemon]) -> Pokemon:
    if not pokemons:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Active encounter has no available Pokemon",
        )
    return random.choice(list(pokemons))


def build_pokeball_reward() -> int:
    return random.randint(POKEBALL_REWARD_MIN, POKEBALL_REWARD_MAX)
