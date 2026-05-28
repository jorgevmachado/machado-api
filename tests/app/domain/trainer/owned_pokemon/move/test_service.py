from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.owned_pokemon.move.service import OwnedPokemonMoveService


def test_from_session_builds_service() -> None:
    service = OwnedPokemonMoveService.from_session(AsyncMock())
    assert isinstance(service, OwnedPokemonMoveService)


@pytest.mark.asyncio
async def test_sync_form_resources_delegates_to_get_or_create() -> None:
    repository = AsyncMock()
    service = OwnedPokemonMoveService(repository=repository)
    move_a = SimpleNamespace(id=uuid4(), pp=10, name="a", deleted_at=None)
    move_b = SimpleNamespace(id=uuid4(), pp=25, name="b", deleted_at=None)
    service.get_or_create = AsyncMock(side_effect=["A", "B"])

    synced = await service.sync_form_resources(
        owned_pokemon_id=uuid4(),
        resources=[move_a, move_b],
    )

    assert synced == ["A", "B"]
    assert service.get_or_create.await_count == 2


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_entity() -> None:
    repository = AsyncMock()
    existing = SimpleNamespace(id=uuid4())
    repository.find_by.return_value = existing
    service = OwnedPokemonMoveService(repository=repository)

    result = await service.get_or_create(resource=SimpleNamespace(id=uuid4(), pp=10), owned_pokemon_id=uuid4())

    assert result is existing
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_saves_missing_entity() -> None:
    repository = AsyncMock()
    created = SimpleNamespace(id=uuid4())
    repository.find_by.return_value = None
    repository.save.return_value = created
    service = OwnedPokemonMoveService(repository=repository)
    move = SimpleNamespace(id=uuid4(), pp=15)

    result = await service.get_or_create(resource=move, owned_pokemon_id=uuid4())

    assert result is created
    repository.save.assert_awaited_once()
