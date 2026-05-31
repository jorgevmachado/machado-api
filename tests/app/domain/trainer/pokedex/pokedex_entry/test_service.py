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


def _build_trainer() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user=SimpleNamespace(id=uuid4()),
    )


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
    service.find_one = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid4(),
            pokemon=SimpleNamespace(status='complete', name='bulbasaur'),
        )
    )

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


@pytest.mark.asyncio
async def test_sync_pokemon_updates_attributes_when_status_is_incomplete() -> None:
    from app.models import PokemonStatusEnum

    repository = AsyncMock()
    repository.update = AsyncMock()

    updated_entity = SimpleNamespace(id=uuid4())
    repository.update.return_value = updated_entity

    entity = SimpleNamespace(
        id=uuid4(),
        hp=10,
        level=1,
        speed=10,
        max_hp=10,
        attack=10,
        defense=10,
        experience=0,
        special_attack=10,
        special_defense=10,
        pokemon=SimpleNamespace(
            status=PokemonStatusEnum.INCOMPLETE,
            name='bulbasaur',
        ),
    )

    pokemon = _build_pokemon()
    service = PokedexEntryService(repository=repository)
    service.find_one = AsyncMock(return_value=entity)
    service.pokemon_service = AsyncMock()
    service.pokemon_service.find_one = AsyncMock(return_value=pokemon)

    result = await service._sync_pokemon(param='bulbasaur', pokedex_id=str(uuid4()))

    assert result is updated_entity
    repository.update.assert_awaited_once_with(entity=entity)


@pytest.mark.asyncio
async def test_sync_pokemon_skips_update_when_pokemon_not_found() -> None:
    from app.models import PokemonStatusEnum

    repository = AsyncMock()

    entity = SimpleNamespace(
        id=uuid4(),
        pokemon=SimpleNamespace(
            status=PokemonStatusEnum.INCOMPLETE,
            name='bulbasaur',
        ),
    )

    service = PokedexEntryService(repository=repository)
    service.find_one = AsyncMock(return_value=entity)
    service.pokemon_service = AsyncMock()
    service.pokemon_service.find_one = AsyncMock(return_value=None)

    result = await service._sync_pokemon(param='bulbasaur')

    assert result is entity
    repository.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_discover_marks_entity_as_discovered_and_updates() -> None:
    updated = SimpleNamespace(id=uuid4(), discovered=True)
    repository = AsyncMock()
    repository.update = AsyncMock(return_value=updated)

    entity = SimpleNamespace(id=uuid4(), discovered=False)
    service = PokedexEntryService(repository=repository, trainer_log=AsyncMock())
    service._sync_pokemon = AsyncMock(return_value=entity)
    trainer = _build_trainer()

    result = await service.discover(pokedex_id='pokedex-id', trainer=trainer, name='bulbasaur')

    assert result is updated
    assert entity.discovered is True
    repository.update.assert_awaited_once_with(entity=entity)


@pytest.mark.asyncio
async def test_discover_returns_entity_without_throw_when_already_discovered() -> None:
    entity = SimpleNamespace(id=uuid4(), discovered=True)
    repository = AsyncMock()
    service = PokedexEntryService(repository=repository, trainer_log=AsyncMock())
    service._sync_pokemon = AsyncMock(return_value=entity)
    trainer = _build_trainer()

    result = await service.discover(
        pokedex_id='pokedex-id',
        trainer=trainer,
        name='bulbasaur',
        without_throw=True,
    )

    assert result is entity
    repository.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_discover_raises_when_already_discovered_and_throw_enabled() -> None:
    from fastapi import HTTPException

    entity = SimpleNamespace(id=uuid4(), discovered=True)
    repository = AsyncMock()
    service = PokedexEntryService(repository=repository, trainer_log=AsyncMock())
    service._sync_pokemon = AsyncMock(return_value=entity)
    trainer = _build_trainer()

    with pytest.raises(HTTPException) as exc_info:
        await service.discover(pokedex_id='pokedex-id', trainer=trainer, name='bulbasaur', without_throw=False)

    assert exc_info.value.status_code == 400
    assert 'already discovered' in exc_info.value.detail
