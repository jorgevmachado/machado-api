from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.trainer.pokedex.pokedex_entry.service import PokedexEntryService


def test_from_session_builds_service() -> None:
    service = PokedexEntryService.from_session(AsyncMock())
    assert isinstance(service, PokedexEntryService)


def _build_pokemon(name: str = "bulbasaur") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        hp=45,
        attack=49,
        defense=49,
        special_attack=65,
        special_defense=65,
        speed=45,
    )


@pytest.mark.asyncio
async def test_sync_from_resources_calls_get_or_create_for_all() -> None:
    repository = AsyncMock()
    service = PokedexEntryService(repository=repository)
    service.get_or_create = AsyncMock(side_effect=["A", "B"])
    discovered_at = datetime.now(tz=timezone.utc)
    discovered_pokemon = SimpleNamespace(id=uuid4())
    resources = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]

    result = await service.sync_from_resources(
        pokedex_id=uuid4(),
        resources=resources,
        discovered_at=discovered_at,
        discovered_pokemon=discovered_pokemon,
    )

    assert result == ["A", "B"]
    assert service.get_or_create.await_count == 2


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_entity() -> None:
    existing = SimpleNamespace(id=uuid4())
    repository = AsyncMock()
    repository.find_by.return_value = existing
    service = PokedexEntryService(repository=repository)

    result = await service.get_or_create(
        pokedex_id=uuid4(),
        pokemon=SimpleNamespace(id=uuid4(), name="bulbasaur"),
        discovered_at=datetime.now(tz=timezone.utc),
        discovered_pokemon=SimpleNamespace(id=uuid4()),
    )

    assert result is existing
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_builds_new_entry_when_missing() -> None:
    created = SimpleNamespace(id=uuid4())
    pokemon = _build_pokemon()
    repository = AsyncMock()
    repository.find_by.return_value = None
    repository.save.return_value = created
    service = PokedexEntryService(repository=repository)

    result = await service.get_or_create(
        pokedex_id=uuid4(),
        pokemon=pokemon,
        discovered_at=datetime.now(tz=timezone.utc),
        discovered_pokemon=pokemon,
    )

    assert result is created
    repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_one_cached_builds_cache_key_with_pokedex_id() -> None:
    repository = AsyncMock()
    service = PokedexEntryService(repository=repository)
    service.cache_service.build_key_one = MagicMock(return_value="entry:key")
    service.cache_service.cache.delete_cache = AsyncMock()
    service.cache_service.get_one = AsyncMock(return_value=None)
    service.cache_service.set_one = AsyncMock()
    service.find_one = AsyncMock(return_value=SimpleNamespace(id=uuid4()))

    await service.find_one_cached(
        param="bulbasaur",
        pokedex_id=str(uuid4()),
        user_request="ash",
        clean_cache=True,
    )

    service.cache_service.cache.delete_cache.assert_awaited_once_with("entry:key")
    service.cache_service.build_key_one.assert_called_once()
    service.find_one.assert_awaited_once()
    service.cache_service.set_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_one_cached_returns_cached_value_without_querying_repository() -> (
    None
):
    repository = AsyncMock()
    service = PokedexEntryService(repository=repository)
    cached = SimpleNamespace(id=uuid4())
    service.cache_service.build_key_one = MagicMock(return_value="entry:key")
    service.cache_service.get_one = AsyncMock(return_value=cached)
    service.find_one = AsyncMock()

    result = await service.find_one_cached(param="bulbasaur", pokedex_id=str(uuid4()))

    assert result is cached
    service.find_one.assert_not_awaited()
