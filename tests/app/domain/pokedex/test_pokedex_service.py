from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi_pagination import LimitOffsetParams

from app.domain.pokedex.service import PokedexService
from app.models.enums import RoleEnum
from app.core.pagination import CustomLimitOffsetPage
from app.shared.schemas import FilterPage


class FakeSession:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


class FakeTrainerService:
    def __init__(self, trainer=None):
        self.trainer = trainer

    async def get_by_user_id(self, _user_id):
        return self.trainer


def build_base_pokemon():
    return SimpleNamespace(
        id=uuid4(),
        name="bulbasaur",
        order=1,
        external_image="https://example.com/bulbasaur.png",
        hp=45,
        attack=49,
        defense=49,
        speed=45,
        special_attack=65,
        special_defense=65,
        types=[],
        deleted_at=None,
    )


def build_pokedex_entity(trainer_id=None, *, discovered=False):
    trainer_id = trainer_id or uuid4()
    return SimpleNamespace(
        id=uuid4(),
        nickname=None,
        level=1,
        experience=0,
        hp=45,
        max_hp=45,
        attack=49,
        defense=49,
        special_attack=65,
        special_defense=65,
        speed=45,
        discovered=discovered,
        discovered_at=datetime.now(timezone.utc) if discovered else None,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        pokemon=SimpleNamespace(
            id=uuid4(),
            name="bulbasaur",
            order=1,
            external_image="https://example.com/bulbasaur.png",
            types=[],
        ),
        trainer=SimpleNamespace(
            id=trainer_id,
            user_id=uuid4(),
            pokeballs=1,
            capture_rate=75,
        ),
    )


class FakeRepository:
    def __init__(self):
        self.session = FakeSession()
        self.created_payload = None
        self.entity = build_pokedex_entity()
        self.pokemons = [build_base_pokemon()]

    async def list_catalog_pokemon(self):
        return self.pokemons

    async def create_for_trainer(self, **kwargs):
        self.created_payload = kwargs
        return [self.entity]

    async def find_owned_detail(self, _trainer_id, _pokemon_name):
        return self.entity

    async def list_owned(self, _trainer_id, _page_filter=None):
        return [self.entity]

    async def mark_discovered(self, entity, *, discovered_at):
        entity.discovered = True
        entity.discovered_at = discovered_at
        return entity


@pytest.mark.asyncio
async def test_initialize_for_trainer_creates_one_entry_per_catalog_pokemon(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
        lambda _min, _max: 1.0,
    )
    repository = FakeRepository()
    service = PokedexService(
        repository,
        FakeTrainerService(
            trainer=SimpleNamespace(
                id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75
            )
        ),
    )

    result = await service.initialize_for_trainer(
        trainer_id=uuid4(),
        discovered_pokemon_name="bulbasaur",
        commit=False,
    )

    assert repository.created_payload is not None
    assert repository.created_payload["discovered_pokemon_name"] == "bulbasaur"
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_all_cached_returns_cache_hit():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    cached = SimpleNamespace(items=[])
    service.list_cache_service.get_list = AsyncMock(return_value=cached)
    service.list_cache_service.delete_domain = AsyncMock()
    service.list_cache_service.set_list = AsyncMock()
    service.repository.list_owned = AsyncMock()

    result = await service.list_all_cached(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
    )

    assert result is cached
    service.repository.list_owned.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_detail_raises_not_found_when_entry_missing():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    service.cache_service.get_one = AsyncMock(return_value=None)
    service.repository.find_owned_detail = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.find_detail(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_discover_marks_entry_and_invalidates_cache():
    repository = FakeRepository()
    repository.entity = build_pokedex_entity(discovered=False)
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    service._invalidate_cache = AsyncMock()

    result = await service.discover(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
    )

    assert result.discovered is True
    service._invalidate_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_all_cached_cleans_cache_and_stores_serialized_list():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    service.list_cache_service.delete_domain = AsyncMock()
    service.list_cache_service.get_list = AsyncMock(return_value=None)
    service.list_cache_service.set_list = AsyncMock()

    page_filter = FilterPage.build(clean_cache=True)
    result = await service.list_all_cached(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        page_filter,
    )

    assert result[0].pokemon.name == "bulbasaur"
    assert page_filter.clean_cache is None
    service.list_cache_service.delete_domain.assert_awaited_once()
    service.list_cache_service.set_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trainer_or_404_raises_when_trainer_does_not_exist():
    service = PokedexService(FakeRepository(), FakeTrainerService(trainer=None))

    with pytest.raises(HTTPException) as exc_info:
        await service._get_trainer_or_404(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER)
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_find_detail_returns_cache_hit_without_querying_repository():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    cached = SimpleNamespace(id="1", pokemon=SimpleNamespace(name="bulbasaur"))
    service.cache_service.get_one = AsyncMock(return_value=cached)
    service.cache_service.set_one = AsyncMock()
    service.repository.find_owned_detail = AsyncMock()

    result = await service.find_detail(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
    )

    assert result is cached
    service.repository.find_owned_detail.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_detail_serializes_and_caches_on_cache_miss():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    service.cache_service.get_one = AsyncMock(return_value=None)
    service.cache_service.set_one = AsyncMock()
    service.repository.find_owned_detail = AsyncMock(return_value=repository.entity)

    result = await service.find_detail(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
    )

    assert result.pokemon.name == "bulbasaur"
    service.cache_service.set_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_discover_raises_not_found_when_entry_is_missing():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    service.repository.find_owned_detail = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.discover(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_discover_skips_mark_when_entry_already_discovered():
    repository = FakeRepository()
    repository.entity = build_pokedex_entity(discovered=True)
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    repository.mark_discovered = AsyncMock()
    service._invalidate_cache = AsyncMock()

    result = await service.discover(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
    )

    assert result.discovered is True
    repository.mark_discovered.assert_not_awaited()
    service._invalidate_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_discover_raises_internal_error_when_reload_fails():
    repository = FakeRepository()
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    service = PokedexService(repository, FakeTrainerService(trainer=trainer))
    service.repository.find_owned_detail = AsyncMock(
        side_effect=[build_pokedex_entity(discovered=False), None]
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.discover(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
        )

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_initialize_for_trainer_commits_and_invalidates_cache_when_enabled(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
        lambda _min, _max: 1.0,
    )
    repository = FakeRepository()
    service = PokedexService(repository, FakeTrainerService())
    service._invalidate_cache = AsyncMock()

    await service.initialize_for_trainer(
        trainer_id=uuid4(),
        discovered_pokemon_name="bulbasaur",
        commit=True,
    )

    assert repository.session.committed is True
    service._invalidate_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_detail_key_when_name_is_provided():
    service = PokedexService(FakeRepository(), FakeTrainerService())
    service.list_cache_service.delete_domain = AsyncMock()
    service.cache_service.cache.delete_cache = AsyncMock()

    await service._invalidate_cache("trainer-id", "bulbasaur")

    service.list_cache_service.delete_domain.assert_awaited_once()
    service.cache_service.cache.delete_cache.assert_awaited_once()


def test_serialize_page_or_list_returns_custom_page_with_serialized_items():
    service = PokedexService(FakeRepository(), FakeTrainerService())
    entity = build_pokedex_entity()
    page = CustomLimitOffsetPage.create(
        items=[entity],
        total=1,
        params=LimitOffsetParams(limit=1, offset=0),
    )

    result = service._serialize_page_or_list(page)

    assert result.items[0].pokemon.name == "bulbasaur"
