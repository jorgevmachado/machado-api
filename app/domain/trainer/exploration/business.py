from __future__ import annotations

import random
from collections.abc import Sequence
from http import HTTPStatus

from fastapi import HTTPException

from app.models import ExplorationEventTypeEnum, Pokemon

POKEBALL_REWARD_MIN = 1
POKEBALL_REWARD_MAX = 3
WILD_EVENT_THRESHOLD = 0.7


def choose_event_type(wild_event_threshold: float = 0.7) -> ExplorationEventTypeEnum:
    if random.random() < wild_event_threshold:
        return ExplorationEventTypeEnum.WILD_POKEMON
    return ExplorationEventTypeEnum.POKEBALLS


def choose_wild_pokemon(pokemons: Sequence[Pokemon]) -> Pokemon:
    if not pokemons:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Active encounter has no available Pokemon",
        )
    return random.choice(list(pokemons))


def build_pokeball_reward(
    pokeball_reward_min: int = 1, pokeball_reward_max: int = 3
) -> int:
    return random.randint(pokeball_reward_min, pokeball_reward_max)
