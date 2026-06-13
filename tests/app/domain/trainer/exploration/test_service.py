from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domain.trainer.exploration.service import ExplorationService
from app.models import ExplorationEventTypeEnum


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.save = AsyncMock()
    repository.update = AsyncMock()
    return repository


def _build_trainer(pokeballs: int = 5):
    return SimpleNamespace(
        id=uuid4(),
        pokeballs=pokeballs,
        user=SimpleNamespace(id=uuid4()),
    )


def _build_trainer_encounter(pokemon_name: str = "pidgey"):
    pokemon = SimpleNamespace(id=uuid4(), name=pokemon_name)
    return SimpleNamespace(
        id=uuid4(),
        pokemon_encounter_id=uuid4(),
        pokemon_encounter=SimpleNamespace(
            id=uuid4(),
            name="route-1",
            pokemons=[pokemon],
        ),
    )


def test_from_session_builds_service():
    service = ExplorationService.from_session(AsyncMock())
    assert isinstance(service, ExplorationService)


@pytest.mark.asyncio
async def test_exploration_creates_wild_pokemon_event(trainer_session: AsyncMock):
    repository = _build_repository(trainer_session)
    trainer = _build_trainer()
    trainer_encounter = _build_trainer_encounter()
    saved = SimpleNamespace(
        id=uuid4(),
        event_type=ExplorationEventTypeEnum.WILD_POKEMON,
        payload={"wild_pokemon_name": "pidgey"},
    )
    repository.save.return_value = saved

    service = ExplorationService(repository=repository, trainer_log=AsyncMock())

    with patch(
        "app.domain.trainer.exploration.service.choose_event_type",
        return_value=ExplorationEventTypeEnum.WILD_POKEMON,
    ):
        result = await service.exploration(
            trainer=trainer, trainer_encounter=trainer_encounter
        )

    assert result is saved
    repository.save.assert_awaited_once()
    entity = repository.save.await_args.kwargs["entity"]
    assert entity.event_type == ExplorationEventTypeEnum.WILD_POKEMON
    assert entity.trainer_id == trainer.id
    assert "wild_pokemon_name" in entity.payload


@pytest.mark.asyncio
async def test_exploration_creates_pokeball_event(trainer_session: AsyncMock):
    repository = _build_repository(trainer_session)
    trainer = _build_trainer(pokeballs=3)
    trainer_encounter = _build_trainer_encounter()
    saved = SimpleNamespace(
        id=uuid4(),
        event_type=ExplorationEventTypeEnum.POKEBALLS,
        payload={"pokeballs_found": 2, "trainer_pokeballs": 5},
    )
    repository.save.return_value = saved

    service = ExplorationService(repository=repository, trainer_log=AsyncMock())

    with (
        patch(
            "app.domain.trainer.exploration.service.choose_event_type",
            return_value=ExplorationEventTypeEnum.POKEBALLS,
        ),
        patch(
            "app.domain.trainer.exploration.service.build_pokeball_reward",
            return_value=2,
        ),
    ):
        result = await service.exploration(
            trainer=trainer, trainer_encounter=trainer_encounter
        )

    assert result is saved
    entity = repository.save.await_args.kwargs["entity"]
    assert entity.payload["pokeballs_found"] == 2
    assert entity.payload["trainer_pokeballs"] == 5


@pytest.mark.asyncio
async def test_exploration_raises_when_save_returns_none(trainer_session: AsyncMock):
    repository = _build_repository(trainer_session)
    repository.save.return_value = None
    trainer = _build_trainer()
    trainer_encounter = _build_trainer_encounter()

    service = ExplorationService(repository=repository, trainer_log=AsyncMock())

    with (
        patch(
            "app.domain.trainer.exploration.service.choose_event_type",
            return_value=ExplorationEventTypeEnum.WILD_POKEMON,
        ),
        pytest.raises(Exception),
    ):
        await service.exploration(trainer=trainer, trainer_encounter=trainer_encounter)


@pytest.mark.asyncio
async def test_update_result_calls_repository_update(trainer_session: AsyncMock):
    repository = _build_repository(trainer_session)
    event = SimpleNamespace(id=uuid4(), payload={"key": "value"})
    updated = SimpleNamespace(id=event.id, payload={"key": "new"})
    repository.update.return_value = updated

    service = ExplorationService(repository=repository, trainer_log=AsyncMock())
    result = await service.update_result(exploration_event=event)

    assert result is updated
    repository.update.assert_awaited_once_with(entity=event)
