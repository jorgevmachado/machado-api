from __future__ import annotations

import random
from collections.abc import Sequence
from http import HTTPStatus

from fastapi import HTTPException

from app.models import ExplorationEventTypeEnum, Pokemon, PokemonEncounter

POKEBALL_REWARD_MIN = 1
POKEBALL_REWARD_MAX = 3
WILD_EVENT_THRESHOLD = 0.7


def resolve_initial_active_encounter(
    encounters: Sequence[PokemonEncounter],
) -> PokemonEncounter | None:
    if not encounters:
        return None
    return sorted(encounters, key=lambda encounter: encounter.order)[0]


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
