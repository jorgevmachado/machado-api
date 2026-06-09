from __future__ import annotations

from fastapi import HTTPException
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.encounter.service import TrainerEncounterService


def _build_trainer(known_encounters=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        known_encounters=known_encounters,
        user=SimpleNamespace(id=uuid4(), username="ash"),
    )


def test_from_session_builds_service() -> None:
    service = TrainerEncounterService.from_session(AsyncMock())
    assert isinstance(service, TrainerEncounterService)


@pytest.mark.asyncio
async def test_sync_from_resources_marks_first_order_as_active() -> None:
    repository = AsyncMock()
    service = TrainerEncounterService(repository=repository, trainer_log=AsyncMock())
    trainer_id = uuid4()
    first = SimpleNamespace(id=uuid4(), order=1)
    second = SimpleNamespace(id=uuid4(), order=2)
    service.get_or_create = AsyncMock(side_effect=["first", "second"])

    result = await service.sync_from_resources(
        trainer_id=trainer_id, encounters=[second, first]
    )

    assert result == ["first", "second"]
    assert service.get_or_create.await_args_list[0].kwargs["is_active"] is False
    assert service.get_or_create.await_args_list[1].kwargs["is_active"] is True


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_entity() -> None:
    existing = SimpleNamespace(id=uuid4())
    repository = AsyncMock()
    repository.find_by.return_value = existing
    service = TrainerEncounterService(repository=repository, trainer_log=AsyncMock())

    result = await service.get_or_create(
        trainer_id=uuid4(),
        encounter=SimpleNamespace(id=uuid4()),
    )

    assert result is existing
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_saves_when_entity_does_not_exist() -> None:
    created = SimpleNamespace(id=uuid4())
    repository = AsyncMock()
    repository.find_by.return_value = None
    repository.save.return_value = created
    service = TrainerEncounterService(repository=repository, trainer_log=AsyncMock())
    encounter = SimpleNamespace(id=uuid4())

    result = await service.get_or_create(
        trainer_id=uuid4(),
        encounter=encounter,
        is_active=True,
    )

    assert result is created
    repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_list_returns_known_encounters_when_provided() -> None:
    known_encounters = [SimpleNamespace(id=uuid4())]
    trainer = _build_trainer(known_encounters=known_encounters)
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())

    result = await service.get_or_create_list(
        trainer=trainer,
        encounters=[SimpleNamespace(id=uuid4(), order=1)],
    )

    assert result is known_encounters


@pytest.mark.asyncio
async def test_get_or_create_list_returns_existing_encounters_from_list_all() -> None:
    existing = [SimpleNamespace(id=uuid4())]
    trainer = _build_trainer(known_encounters=None)
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.list_all = AsyncMock(return_value=existing)

    result = await service.get_or_create_list(
        trainer=trainer,
        encounters=[SimpleNamespace(id=uuid4(), order=1)],
    )

    assert result is existing


@pytest.mark.asyncio
async def test_get_or_create_list_returns_empty_when_encounters_are_missing() -> None:
    trainer = _build_trainer(known_encounters=None)
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.list_all = AsyncMock(return_value=[])
    service.sync_from_resources = AsyncMock()

    result = await service.get_or_create_list(
        trainer=trainer,
        encounters=None,
    )

    assert result == []
    service.sync_from_resources.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_list_syncs_when_no_known_or_existing_encounters() -> None:
    expected = [SimpleNamespace(id=uuid4())]
    encounters = [SimpleNamespace(id=uuid4(), order=1)]
    trainer = _build_trainer(known_encounters=[])
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.list_all = AsyncMock(return_value=[])
    service.sync_from_resources = AsyncMock(return_value=expected)

    result = await service.get_or_create_list(
        trainer=trainer,
        encounters=encounters,
    )

    assert result is expected
    service.sync_from_resources.assert_awaited_once_with(
        trainer_id=trainer.id,
        encounters=encounters,
    )


@pytest.mark.asyncio
async def test_update_list_creates_missing_encounters_and_returns_all() -> None:
    trainer = _build_trainer()
    encounter_id = uuid4()
    known_encounter = SimpleNamespace(pokemon_encounter_id=encounter_id)
    new_encounter = SimpleNamespace(id=uuid4())

    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.list_all = AsyncMock(side_effect=[
        [known_encounter],
        [known_encounter, SimpleNamespace(pokemon_encounter_id=new_encounter.id)],
    ])
    service.get_or_create = AsyncMock()

    result = await service.update_list(
        trainer=trainer,
        encounters=[SimpleNamespace(id=encounter_id), new_encounter],
    )

    service.get_or_create.assert_awaited_once_with(
        trainer_id=trainer.id,
        encounter=new_encounter,
        is_active=False,
    )
    assert len(result) == 2


@pytest.mark.asyncio
async def test_update_list_skips_already_known_encounters() -> None:
    trainer = _build_trainer()
    encounter_id = uuid4()
    known_encounter = SimpleNamespace(pokemon_encounter_id=encounter_id)

    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.list_all = AsyncMock(return_value=[known_encounter])
    service.get_or_create = AsyncMock()

    await service.update_list(
        trainer=trainer,
        encounters=[SimpleNamespace(id=encounter_id)],
    )

    service.get_or_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_list_returns_empty_when_no_encounters() -> None:
    trainer = _build_trainer()
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.list_all = AsyncMock(return_value=[])

    result = await service.update_list(
        trainer=trainer,
        encounters=[],
    )

    assert result == []


@pytest.mark.asyncio
async def test_select_active_returns_active_encounter() -> None:
    trainer = _build_trainer()
    previous_encounter_active = SimpleNamespace(id=uuid4(), is_active=True)
    current_encounter_active = SimpleNamespace(id=uuid4(), is_active=False)
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())

    service.repository.find_by = AsyncMock(return_value=current_encounter_active)
    service._deactivate_all_encounters = AsyncMock(
        return_value=[previous_encounter_active, current_encounter_active]
    )

    service.repository.update = AsyncMock(return_value=current_encounter_active)

    result = await service.select_active(
        trainer=trainer,
        encounter_id=current_encounter_active.id,
    )

    assert result == current_encounter_active
    service.repository.find_by.assert_awaited_once_with(
        trainer_id=trainer.id,
        pokemon_encounter_id=current_encounter_active.id,
    )
    service._deactivate_all_encounters.assert_awaited_once_with(trainer=trainer)
    service.repository.update.assert_awaited_once_with(entity=current_encounter_active)
    service.trainer_log.create.assert_awaited_once()

@pytest.mark.asyncio
async def test_select_active_returns_throw() -> None:
    trainer = _build_trainer()
    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())
    service.repository.find_by = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.select_active(trainer=trainer, encounter_id=uuid4())


    assert exc_info.value.status_code == 404
    service.trainer_log.create.assert_awaited_once()

@pytest.mark.asyncio
async def test_deactivate_all_encounters_returns_all_inactive_encounters() -> None:
    trainer = _build_trainer()
    encounter_active = SimpleNamespace(id="encounter_active_one", is_active=True)

    service = TrainerEncounterService(repository=AsyncMock(), trainer_log=AsyncMock())

    service.list_all = AsyncMock(return_value=[encounter_active])

    encounter_active.is_active = False
    service.repository.update = AsyncMock(return_value=encounter_active)

    result = await service._deactivate_all_encounters(trainer=trainer)

    assert result == [encounter_active]
