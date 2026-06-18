from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.pokedex.service import PokedexService
from app.domain.trainer.progression import AttributesCalculatedSchema
from app.shared.schemas import FilterPage


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.find_by = AsyncMock()
    return repository


def test_from_session_builds_service() -> None:
    service = PokedexService.from_session(AsyncMock())
    assert isinstance(service, PokedexService)


def test_init_builds_default_dependencies_from_session(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    with (
        patch(
            "app.domain.trainer.pokedex.service.PokemonService.from_session"
        ) as pokemon_from_session,
        patch(
            "app.domain.trainer.pokedex.service.PokedexEntryService.from_session"
        ) as entry_from_session,
    ):
        pokemon_from_session.return_value = AsyncMock()
        entry_from_session.return_value = AsyncMock()
        PokedexService(repository=repository)
        pokemon_from_session.assert_called_once_with(trainer_session)
        entry_from_session.assert_called_once_with(trainer_session)


@pytest.mark.asyncio
async def test_create_returns_fresh_pokedex_and_commits(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4())
    pokemon_service = AsyncMock()
    pokemon_service.list_all.return_value = [
        SimpleNamespace(id=uuid4(), name="bulbasaur")
    ]
    pokedex_entry_service = AsyncMock()
    service = PokedexService(
        repository=repository,
        pokemon_service=pokemon_service,
        pokedex_entry_service=pokedex_entry_service,
    )
    service.cache_service.delete_domain = AsyncMock()

    result = await service.create(
        trainer_id=uuid4(),
        discovered_pokemon=SimpleNamespace(id=uuid4()),
        discovered_at=datetime.now(tz=timezone.utc),
        commit=True,
    )

    assert result is repository.find_by.return_value
    trainer_session.add.assert_called_once()
    trainer_session.flush.assert_awaited_once()
    trainer_session.commit.assert_awaited_once()
    trainer_session.refresh.assert_awaited_once()
    pokedex_entry_service.sync_from_resources.assert_awaited_once()
    service.cache_service.delete_domain.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_without_commit_skips_commit_refresh_and_cache(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4())
    service = PokedexService(
        repository=repository,
        pokemon_service=AsyncMock(list_all=AsyncMock(return_value=[])),
        pokedex_entry_service=AsyncMock(),
    )
    service.cache_service.delete_domain = AsyncMock()

    await service.create(
        trainer_id=uuid4(),
        discovered_pokemon=SimpleNamespace(id=uuid4()),
        discovered_at=datetime.now(tz=timezone.utc),
        commit=False,
    )

    trainer_session.commit.assert_not_awaited()
    trainer_session.refresh.assert_not_awaited()
    service.cache_service.delete_domain.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rolls_back_and_raises_when_fresh_not_found(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = None
    service = PokedexService(
        repository=repository,
        pokemon_service=AsyncMock(list_all=AsyncMock(return_value=[])),
        pokedex_entry_service=AsyncMock(),
    )

    with pytest.raises(HTTPException, match="Could not load created Pokedex"):
        await service.create(
            trainer_id=uuid4(),
            discovered_pokemon=SimpleNamespace(id=uuid4()),
            discovered_at=datetime.now(tz=timezone.utc),
            commit=True,
        )

    trainer_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_raises_when_trainer_id_missing(
    trainer_session: AsyncMock,
) -> None:
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
    )

    with pytest.raises(HTTPException, match="Trainer ID is required"):
        await service.get_by(None)


@pytest.mark.asyncio
async def test_get_by_returns_cached_id_and_cleans_cache(
    trainer_session: AsyncMock,
) -> None:
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
    )
    service.cache_service.build_key_one = MagicMock(return_value="pokedex:key")
    service.cache_service.delete_cache = AsyncMock()
    service.cache_service.cache.get_cache = AsyncMock(return_value={"id": "cached-id"})

    result = await service.get_by(trainer_id=str(uuid4()), clean_cache=True)

    assert result == "cached-id"
    service.cache_service.delete_cache.assert_awaited_once_with(cache_key="pokedex:key")


@pytest.mark.asyncio
async def test_get_by_loads_from_repository_and_sets_cache(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4())
    service = PokedexService(
        repository=repository,
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
    )
    service.cache_service.build_key_one = MagicMock(return_value="pokedex:key")
    service.cache_service.cache.get_cache = AsyncMock(return_value=None)
    service.cache_service.set_cache = AsyncMock()

    result = await service.get_by(trainer_id=str(uuid4()))

    assert result == str(repository.find_by.return_value.id)
    service.cache_service.set_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_raises_not_found_when_repository_returns_none(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = None
    service = PokedexService(
        repository=repository,
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
    )
    service.cache_service.build_key_one = MagicMock(return_value="pokedex:key")
    service.cache_service.cache.get_cache = AsyncMock(return_value=None)

    with pytest.raises(HTTPException, match="Pokedex not found"):
        await service.get_by(trainer_id=str(uuid4()))


@pytest.mark.asyncio
async def test_list_all_cached_delegates_to_pokedex_entry_service(
    trainer_session: AsyncMock,
) -> None:
    pokedex_entry_service = AsyncMock()
    pokedex_entry_service.list_all_cached.return_value = SimpleNamespace(items=[])
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=pokedex_entry_service,
    )
    service.get_by = AsyncMock(return_value="pokedex-id")
    page_filter = FilterPage.build(trainer_id=str(uuid4()), clean_cache=True, limit=10)

    result = await service.list_all_cached(page_filter=page_filter, user_request="ash")

    assert result is pokedex_entry_service.list_all_cached.return_value
    assert (
        pokedex_entry_service.list_all_cached.await_args.kwargs[
            "page_filter"
        ].pokedex_id
        == "pokedex-id"
    )


@pytest.mark.asyncio
async def test_find_one_cached_delegates_to_pokedex_entry_service(
    trainer_session: AsyncMock,
) -> None:
    pokedex_entry_service = AsyncMock()
    pokedex_entry_service.find_one_cached.return_value = SimpleNamespace(id=uuid4())
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=pokedex_entry_service,
    )
    service.get_by = AsyncMock(return_value="pokedex-id")

    result = await service.find_one_cached(
        param="bulbasaur",
        trainer_id=str(uuid4()),
        clean_cache=False,
        user_request="ash",
    )

    assert result is pokedex_entry_service.find_one_cached.return_value
    pokedex_entry_service.find_one_cached.assert_awaited_once_with(
        param="bulbasaur",
        pokedex_id="pokedex-id",
        clean_cache=False,
        user_request="ash",
    )


@pytest.mark.asyncio
async def test_get_or_create_returns_given_pokedex_without_querying() -> None:
    pokedex = SimpleNamespace(id=uuid4())
    service = PokedexService(
        repository=_build_repository(AsyncMock()),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
        trainer_log=AsyncMock(),
    )
    service.find_by = AsyncMock()
    service.create = AsyncMock()
    trainer = SimpleNamespace(id=uuid4(), pokedex=pokedex, user_id=uuid4())

    result = await service.get_or_create(trainer=trainer)

    assert result is pokedex
    service.find_by.assert_not_awaited()
    service.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_pokedex_when_found() -> None:
    existing = SimpleNamespace(id=uuid4())
    service = PokedexService(
        repository=_build_repository(AsyncMock()),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
        trainer_log=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=existing)
    service.create = AsyncMock()
    trainer = SimpleNamespace(id=uuid4(), pokedex=None, user_id=uuid4())

    result = await service.get_or_create(trainer=trainer)

    assert result is existing
    service.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_creates_when_pokedex_does_not_exist() -> None:
    created = SimpleNamespace(id=uuid4())
    discovered_pokemon = SimpleNamespace(id=uuid4())
    trainer = SimpleNamespace(id=uuid4(), pokedex=None, user_id=uuid4())
    service = PokedexService(
        repository=_build_repository(AsyncMock()),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=AsyncMock(),
        trainer_log=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=None)
    service.create = AsyncMock(return_value=created)

    result = await service.get_or_create(
        trainer=trainer,
        commit=False,
        discovered_at=datetime.now(tz=timezone.utc),
        discovered_pokemon=discovered_pokemon,
    )

    assert result is created
    service.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_discover_delegates_to_pokedex_entry_service(
    trainer_session: AsyncMock,
) -> None:
    entry = SimpleNamespace(id=uuid4(), discovered=True)
    pokedex_entry_service = AsyncMock()
    pokedex_entry_service.discover = AsyncMock(return_value=entry)
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=pokedex_entry_service,
    )
    service.get_by = AsyncMock(return_value="pokedex-id")
    trainer_id = uuid4()
    trainer = SimpleNamespace(id=trainer_id)

    result = await service.discover(
        trainer=trainer, name="bulbasaur", without_throw=True
    )

    assert result is entry
    service.get_by.assert_awaited_once_with(trainer_id=str(trainer_id))
    pokedex_entry_service.discover.assert_awaited_once_with(
        name="bulbasaur",
        trainer=trainer,
        pokedex_id="pokedex-id",
        without_throw=True,
    )


@pytest.mark.asyncio
async def test_update_after_battle_returns_same_entry_when_no_changes(
    trainer_session: AsyncMock,
) -> None:
    trainer = SimpleNamespace(id=uuid4(), user=SimpleNamespace(username="ash"))
    entry = SimpleNamespace(
        id=uuid4(),
        hp=30,
        level=5,
        speed=10,
        attack=10,
        max_hp=40,
        defense=10,
        experience=100,
        special_attack=10,
        special_defense=10,
    )
    progression = AttributesCalculatedSchema(
        hp=30,
        level=5,
        speed=10,
        attack=10,
        max_hp=40,
        defense=10,
        level_up=False,
        experience=100,
        special_attack=10,
        special_defense=10,
    )
    entry_service = AsyncMock()
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=entry_service,
    )
    service.find_one = AsyncMock()

    result = await service.update_after_battle(
        trainer=trainer,
        pokedex_entry=entry,
        pokedex_entry_progression=progression,
    )

    assert result is entry
    entry_service.update_entity.assert_not_awaited()
    service.find_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_after_battle_updates_and_reloads_entry(
    trainer_session: AsyncMock,
) -> None:
    trainer = SimpleNamespace(id=uuid4(), user=SimpleNamespace(username="ash"))
    entry = SimpleNamespace(
        id=uuid4(),
        hp=30,
        level=5,
        speed=10,
        attack=10,
        max_hp=40,
        defense=10,
        experience=100,
        special_attack=10,
        special_defense=10,
    )
    progression = AttributesCalculatedSchema(
        hp=45,
        level=6,
        speed=20,
        attack=21,
        max_hp=50,
        defense=22,
        level_up=True,
        experience=200,
        special_attack=23,
        special_defense=24,
    )
    entry_service = AsyncMock()
    service = PokedexService(
        repository=_build_repository(trainer_session),
        pokemon_service=AsyncMock(),
        pokedex_entry_service=entry_service,
    )
    reloaded = SimpleNamespace(id=entry.id)
    service.find_one = AsyncMock(return_value=reloaded)

    result = await service.update_after_battle(
        trainer=trainer,
        pokedex_entry=entry,
        pokedex_entry_progression=progression,
    )

    assert result is reloaded
    assert entry.hp == 45
    assert entry.level == 6
    assert entry.speed == 20
    entry_service.update_entity.assert_awaited_once_with(entity=entry)
