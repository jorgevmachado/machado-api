from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.encounter.service import TrainerEncounterService


def test_from_session_builds_service() -> None:
    service = TrainerEncounterService.from_session(AsyncMock())
    assert isinstance(service, TrainerEncounterService)


@pytest.mark.asyncio
async def test_sync_from_resources_marks_first_order_as_active() -> None:
    repository = AsyncMock()
    service = TrainerEncounterService(repository=repository)
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
    service = TrainerEncounterService(repository=repository)

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
    service = TrainerEncounterService(repository=repository)
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
    service = TrainerEncounterService(repository=AsyncMock())

    result = await service.get_or_create_list(
        trainer_id=uuid4(),
        known_encounters=known_encounters,
        encounters=[SimpleNamespace(id=uuid4(), order=1)],
    )

    assert result is known_encounters


@pytest.mark.asyncio
async def test_get_or_create_list_returns_existing_encounters_from_list_all() -> None:
    existing = [SimpleNamespace(id=uuid4())]
    service = TrainerEncounterService(repository=AsyncMock())
    service.list_all = AsyncMock(return_value=existing)

    result = await service.get_or_create_list(
        trainer_id=uuid4(),
        known_encounters=None,
        encounters=[SimpleNamespace(id=uuid4(), order=1)],
    )

    assert result is existing


@pytest.mark.asyncio
async def test_get_or_create_list_returns_empty_when_encounters_are_missing() -> None:
    service = TrainerEncounterService(repository=AsyncMock())
    service.list_all = AsyncMock(return_value=[])
    service.sync_from_resources = AsyncMock()

    result = await service.get_or_create_list(
        trainer_id=uuid4(),
        known_encounters=None,
        encounters=None,
    )

    assert result == []
    service.sync_from_resources.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_list_syncs_when_no_known_or_existing_encounters() -> None:
    expected = [SimpleNamespace(id=uuid4())]
    encounters = [SimpleNamespace(id=uuid4(), order=1)]
    trainer_id = uuid4()
    service = TrainerEncounterService(repository=AsyncMock())
    service.list_all = AsyncMock(return_value=[])
    service.sync_from_resources = AsyncMock(return_value=expected)

    result = await service.get_or_create_list(
        trainer_id=trainer_id,
        known_encounters=[],
        encounters=encounters,
    )

    assert result is expected
    service.sync_from_resources.assert_awaited_once_with(
        trainer_id=trainer_id,
        encounters=encounters,
    )
