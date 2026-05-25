from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.trainer_party import (
    TrainerPartyService,
    UpdateTrainerPartySchema,
)
from app.models.enums import PokemonStatusEnum


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


def build_pokemon(name="bulbasaur"):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        order=1,
        hp=45,
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
        external_image="https://example.com/pokemon.png",
        special_attack=65,
        special_defense=65,
        base_experience=64,
        evolution_chain=None,
        evolves_from_species=None,
        has_gender_differences=False,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        types=[],
        deleted_at=None,
    )


def build_trainer():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        pokeballs=3,
        capture_rate=75,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
    )


def build_my_pokemon(trainer, pokemon=None):
    pokemon = pokemon or build_pokemon()
    return SimpleNamespace(
        id=uuid4(),
        name=f"{pokemon.name}-owned",
        nickname=pokemon.name.title(),
        level=5,
        experience=0,
        hp=20,
        max_hp=20,
        attack=10,
        defense=10,
        special_attack=10,
        special_defense=10,
        speed=10,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        pokemon=pokemon,
        trainer=trainer,
        moves=[
            SimpleNamespace(
                id=uuid4(),
                pp=10,
                max_pp=15,
                deleted_at=None,
                pokemon_move_id=uuid4(),
                pokemon_move=SimpleNamespace(
                    name="tackle",
                    type="normal",
                    power=40,
                    accuracy=100,
                ),
            )
        ],
    )


def build_party_entry(my_pokemon, slot=1):
    return SimpleNamespace(
        id=uuid4(),
        slot=slot,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
        my_pokemon=my_pokemon,
    )


class FakeTrainerService:
    def __init__(self, trainer=None):
        self.trainer = trainer
        self.invalidate_home_cache = AsyncMock()

    async def get_by_user_id(self, _user_id):
        return self.trainer


class FakeRepository:
    def __init__(self, trainer):
        self.session = FakeSession()
        self.trainer = trainer
        self.party_entries = []
        self.owned_my_pokemons = []
        self.soft_deleted_at = None

    async def list_active_party(self, _trainer_id):
        return self.party_entries

    async def soft_delete_active_party(self, _trainer_id, deleted_at):
        self.soft_deleted_at = deleted_at
        self.party_entries = []

    async def list_owned_my_pokemon(self, _trainer_id, _my_pokemon_ids):
        return self.owned_my_pokemons

    async def create_party(self, *, trainer_id, my_pokemons):
        self.party_entries = [
            build_party_entry(my_pokemon, slot=index)
            for index, my_pokemon in enumerate(my_pokemons, start=1)
        ]
        return self.party_entries


def build_service(repository, trainer):
    trainer_service = FakeTrainerService(trainer)
    service = TrainerPartyService(
        repository,
        trainer_service=trainer_service,
    )
    service.party_cache_service.get_list = AsyncMock(return_value=None)
    service.party_cache_service.set_list = AsyncMock()
    service.party_cache_service.cache.delete_cache = AsyncMock()
    return service, trainer_service


@pytest.mark.asyncio
async def test_update_party_raises_for_invalid_owned_pokemon_ids():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    repository.owned_my_pokemons = [build_my_pokemon(trainer)]
    service, _trainer_service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_party(
            trainer=trainer,
            payload=UpdateTrainerPartySchema(my_pokemon_ids=[uuid4(), uuid4()]),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_party_replaces_active_party_and_invalidates_caches():
    trainer = build_trainer()
    owned = [build_my_pokemon(trainer), build_my_pokemon(trainer, build_pokemon("squirtle"))]
    repository = FakeRepository(trainer)
    repository.owned_my_pokemons = owned
    service, trainer_service = build_service(repository, trainer)

    result = await service.update_party(
        trainer=trainer,
        payload=UpdateTrainerPartySchema(my_pokemon_ids=[owned[0].id, owned[1].id]),
    )

    assert [entry.slot for entry in result] == [1, 2]
    assert repository.soft_deleted_at is not None
    assert repository.session.commits == 1
    service.party_cache_service.cache.delete_cache.assert_awaited_once()
    trainer_service.invalidate_home_cache.assert_awaited_once_with(str(trainer.id))


@pytest.mark.asyncio
async def test_get_party_returns_cache_hit_without_querying_repository():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service, _trainer_service = build_service(repository, trainer)
    cached = [SimpleNamespace(id="party-cached")]
    service.party_cache_service.get_list = AsyncMock(return_value=cached)
    repository.list_active_party = AsyncMock()

    result = await service.get_party(trainer=trainer, )

    assert result == cached
    repository.list_active_party.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_party_by_trainer_id_serializes_and_caches_repository_entries():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    repository.party_entries = [build_party_entry(build_my_pokemon(trainer))]
    service, _trainer_service = build_service(repository, trainer)

    result = await service.get_party_by_trainer_id(trainer.id)

    assert len(result) == 1
    assert result[0].my_pokemon.moves[0].pokemon_move_name == "tackle"
    service.party_cache_service.set_list.assert_awaited_once()
