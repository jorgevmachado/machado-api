from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domain.trainer.trainer_exploration import (
    MAX_PARTY_SIZE,
    POKEBALL_REWARD_MAX,
    POKEBALL_REWARD_MIN,
    WILD_EVENT_THRESHOLD,
    build_pokeball_reward,
    choose_event_type,
    choose_wild_pokemon,
    resolve_initial_active_encounter,
    validate_party_selection,
)
from app.models.enums import ExplorationEventTypeEnum


def test_resolve_initial_active_encounter_returns_none_without_encounters():
    assert resolve_initial_active_encounter([]) is None


def test_resolve_initial_active_encounter_uses_lowest_order():
    encounters = [
        SimpleNamespace(id="2", order=3),
        SimpleNamespace(id="1", order=1),
    ]

    result = resolve_initial_active_encounter(encounters)

    assert result.id == "1"


def test_validate_party_selection_rejects_more_than_max_size():
    with pytest.raises(HTTPException) as exc_info:
        validate_party_selection(list(range(MAX_PARTY_SIZE + 1)))

    assert exc_info.value.status_code == 400


def test_validate_party_selection_rejects_duplicates():
    with pytest.raises(HTTPException) as exc_info:
        validate_party_selection(["1", "1"])

    assert exc_info.value.status_code == 400


def test_choose_event_type_returns_wild_event_below_threshold(monkeypatch):
    monkeypatch.setattr(
        "app.domain.trainer.trainer_exploration.business.random.random",
        lambda: WILD_EVENT_THRESHOLD - 0.01,
    )

    assert choose_event_type() == ExplorationEventTypeEnum.WILD_POKEMON


def test_choose_event_type_returns_pokeballs_event_at_or_above_threshold(monkeypatch):
    monkeypatch.setattr(
        "app.domain.trainer.trainer_exploration.business.random.random",
        lambda: WILD_EVENT_THRESHOLD,
    )

    assert choose_event_type() == ExplorationEventTypeEnum.POKEBALLS


def test_choose_wild_pokemon_raises_without_available_options():
    with pytest.raises(HTTPException) as exc_info:
        choose_wild_pokemon([])

    assert exc_info.value.status_code == 400


def test_choose_wild_pokemon_delegates_to_random_choice(monkeypatch):
    chosen = SimpleNamespace(id="pokemon-1")
    monkeypatch.setattr(
        "app.domain.trainer.trainer_exploration.business.random.choice",
        lambda options: options[0],
    )

    assert choose_wild_pokemon([chosen]) is chosen


def test_build_pokeball_reward_uses_configured_range(monkeypatch):
    monkeypatch.setattr(
        "app.domain.trainer.trainer_exploration.business.random.randint",
        lambda minimum, maximum: (
            minimum == POKEBALL_REWARD_MIN and maximum == POKEBALL_REWARD_MAX and 2
        ),
    )

    assert build_pokeball_reward() == 2
