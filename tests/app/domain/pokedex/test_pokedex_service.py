from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.pokedex.service import PokedexService
from app.models.enums import PokemonStatusEnum
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
        moves=[],
        images=None,
        speed=45,
        height=7,
        weight=69,
        shape=None,
        status=PokemonStatusEnum.COMPLETE,
        attack=49,
        defense=49,
        is_baby=False,
        habitat=None,
        abilities=[],
        evolutions=[],
        encounters=[],
        growth_rate=None,
        gender_rate=1,
        is_mythical=False,
        description=None,
        is_legendary=False,
        capture_rate=45,
        hatch_counter=20,
        base_happiness=50,
        external_image="https://example.com/bulbasaur.png",
        hp=45,
        special_attack=65,
        special_defense=65,
        types=[],
        base_experience=64,
        evolution_chain=None,
        evolves_from_species=None,
        has_gender_differences=False,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
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
        pokemon=build_base_pokemon(),
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

    async def find_by(self, **kwargs):
        return await self.find_owned_detail(
            kwargs.get("trainer_id"),
            kwargs.get("name") or kwargs.get("pokemon_name"),
        )

    async def list_all(self, page_filter=None):
        trainer_id = getattr(page_filter, "trainer_id", None) if page_filter else None
        return await self.list_owned(trainer_id, page_filter)

    async def mark_discovered(self, entity, *, discovered_at):
        entity.discovered = True
        entity.discovered_at = discovered_at
        return entity







@pytest.mark.asyncio
async def test_list_all_cached_uses_passthrough_branch_when_trainer_id_is_provided():
    repository = FakeRepository()
    service = PokedexService(repository, FakeTrainerService())
    service.list_cache_service.get_list = AsyncMock(return_value=None)
    service.list_cache_service.set_list = AsyncMock()

    result = await service.list_all_cached(
        page_filter=FilterPage.build(limit=10, offset=0),
        user_request='request',
        trainer_id=str(uuid4()),
    )

    assert len(result) == 1
    service.list_cache_service.set_list.assert_awaited_once()




@pytest.mark.asyncio
async def test_initialize_for_trainer_uses_empty_list_when_pokemon_service_returns_non_list():
    repository = FakeRepository()
    pokemon_service = AsyncMock()
    pokemon_service.list_all.return_value = {'unexpected': 'shape'}
    service = PokedexService(
        repository,
        FakeTrainerService(),
        pokemon_service,
    )
    service._create_for_trainer = AsyncMock(return_value=[])
    service._invalidate_cache = AsyncMock()

    result = await service.initialize_for_trainer(
        trainer_id=uuid4(),
        discovered_pokemon_name='bulbasaur',
        commit=False,
    )

    assert result == []
    service._create_for_trainer.assert_awaited_once()
    create_call = service._create_for_trainer.await_args.kwargs
    assert create_call['pokemons'] == []
    assert create_call['attributes_by_pokemon_id'] == {}
    assert repository.session.committed is False
    service._invalidate_cache.assert_not_awaited()


@pytest.mark.asyncio
async def test_initialize_for_trainer_commits_and_returns_only_found_entities():
    repository = FakeRepository()
    pokemon_a = build_base_pokemon()
    pokemon_b = build_base_pokemon()
    pokemon_b.name = 'ivysaur'
    pokemon_service = AsyncMock()
    pokemon_service.list_all.return_value = [pokemon_a, pokemon_b]
    entity = build_pokedex_entity(discovered=True)
    repository.find_by = AsyncMock(side_effect=[entity, None])
    service = PokedexService(
        repository,
        FakeTrainerService(),
        pokemon_service,
    )
    service._create_for_trainer = AsyncMock(return_value=[entity])
    service._invalidate_cache = AsyncMock()
    trainer_id = uuid4()

    result = await service.initialize_for_trainer(
        trainer_id=trainer_id,
        discovered_pokemon_name='bulbasaur',
        commit=True,
    )

    assert result == [entity]
    assert repository.session.committed is True
    service._create_for_trainer.assert_awaited_once()
    create_call = service._create_for_trainer.await_args.kwargs
    assert create_call['pokemons'] == [pokemon_a, pokemon_b]
    assert set(create_call['attributes_by_pokemon_id'].keys()) == {pokemon_a.id, pokemon_b.id}
    service._invalidate_cache.assert_awaited_once_with(
        identifier='bulbasaur',
        trainer_id=str(trainer_id),
    )
