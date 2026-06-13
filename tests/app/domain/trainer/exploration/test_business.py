from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.exploration.business import (
    build_pokeball_reward,
    choose_event_type,
    choose_wild_pokemon,
    POKEBALL_REWARD_MAX,
    POKEBALL_REWARD_MIN,
)
from app.models import ExplorationEventTypeEnum


# ── choose_event_type ─────────────────────────────────────────────────────────


def test_choose_event_type_returns_wild_pokemon_when_below_threshold():
    with patch(
        "app.domain.trainer.exploration.business.random.random", return_value=0.3
    ):
        result = choose_event_type()
    assert result == ExplorationEventTypeEnum.WILD_POKEMON


def test_choose_event_type_returns_pokeballs_when_above_threshold():
    with patch(
        "app.domain.trainer.exploration.business.random.random", return_value=0.9
    ):
        result = choose_event_type()
    assert result == ExplorationEventTypeEnum.POKEBALLS


def test_choose_event_type_accepts_custom_threshold():
    with patch(
        "app.domain.trainer.exploration.business.random.random", return_value=0.5
    ):
        assert (
            choose_event_type(wild_event_threshold=0.6)
            == ExplorationEventTypeEnum.WILD_POKEMON
        )
        assert (
            choose_event_type(wild_event_threshold=0.4)
            == ExplorationEventTypeEnum.POKEBALLS
        )


# ── choose_wild_pokemon ───────────────────────────────────────────────────────


def test_choose_wild_pokemon_raises_when_no_pokemons():
    with pytest.raises(HTTPException) as exc_info:
        choose_wild_pokemon([])
    assert exc_info.value.status_code == 400


def test_choose_wild_pokemon_returns_one_from_list():
    from types import SimpleNamespace

    pokemon = SimpleNamespace(id=uuid4(), name="pidgey")
    result = choose_wild_pokemon([pokemon])
    assert result is pokemon


def test_choose_wild_pokemon_returns_random_choice():
    from types import SimpleNamespace

    p1 = SimpleNamespace(id=uuid4(), name="pidgey")
    p2 = SimpleNamespace(id=uuid4(), name="rattata")
    with patch(
        "app.domain.trainer.exploration.business.random.choice", return_value=p2
    ):
        result = choose_wild_pokemon([p1, p2])
    assert result is p2


# ── build_pokeball_reward ─────────────────────────────────────────────────────


def test_build_pokeball_reward_is_within_default_range():
    for _ in range(20):
        result = build_pokeball_reward()
        assert POKEBALL_REWARD_MIN <= result <= POKEBALL_REWARD_MAX


def test_build_pokeball_reward_accepts_custom_range():
    with patch(
        "app.domain.trainer.exploration.business.random.randint", return_value=5
    ) as mock_randint:
        result = build_pokeball_reward(pokeball_reward_min=5, pokeball_reward_max=10)
    mock_randint.assert_called_once_with(5, 10)
    assert result == 5
