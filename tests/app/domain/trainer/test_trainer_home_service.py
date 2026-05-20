from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.service import TrainerService
from app.models.enums import PokemonStatusEnum


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
        my_pokemons=[],
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
        moves=[],
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


def build_encounter(name="route-1", order=1):
    return SimpleNamespace(
        id=uuid4(),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
        pokemon_encounter=SimpleNamespace(
            id=uuid4(),
            url="https://example.com/encounters/1",
            name=name,
            order=order,
            chance=30,
            method="walk",
            version="red",
            min_level=2,
            max_level=4,
            condition="day",
            max_chance=30,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            deleted_at=None,
            pokemons=[build_pokemon()],
        ),
    )


def build_pokedex_entry(trainer, pokemon=None):
    pokemon = pokemon or build_pokemon()
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
        discovered=True,
        discovered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        pokemon=pokemon,
        trainer=trainer,
    )


class FakeRepository:
    def __init__(self, trainer=None):
        self.session = AsyncMock()
        self.trainer = trainer

    async def find_by(self, **kwargs):
        return self.trainer


class FakeTrainerPartyService:
    def __init__(self, party):
        self.party = party

    async def list_all(self, page_filter=None):
        return self.party


class FakeTrainerEncounterService:
    def __init__(self, encounter):
        self.encounter = encounter
        self.added_payload = None

    async def get_active_encounter_by_trainer_id(self, _trainer_id):
        return self.encounter

    async def list_all(self, trainer_id=None):
        return [self.encounter] if self.encounter is not None else []

    async def add_encounters(self, trainer_id=None, pokemon_encounters=None):
        self.added_payload = {
            "trainer_id": trainer_id,
            "pokemon_encounters": pokemon_encounters or [],
        }
        return pokemon_encounters or []


class FakePokedexService:
    def __init__(self, latest_discoveries):
        self.latest_discoveries = latest_discoveries

    async def list_latest_discoveries(self, _trainer_id):
        return self.latest_discoveries


class FakeBattleSessionService:
    def __init__(self, active_battle=None):
        self.active_battle = active_battle

    async def get_active_battle_summary_by_trainer_id(self, _trainer_id):
        return self.active_battle


def build_service(
    trainer=None,
    encounter=None,
    party=None,
    latest_discoveries=None,
    active_battle=None,
):
    repository = FakeRepository(trainer=trainer)
    service = TrainerService(
        repository,
        my_pokemon_service=AsyncMock(),
        pokedex_service=FakePokedexService(latest_discoveries or []),
        trainer_encounter_service=FakeTrainerEncounterService(encounter),
        trainer_party_service=FakeTrainerPartyService(party or []),
        battle_session_service=FakeBattleSessionService(active_battle),
    )
    service.home_cache_service.get_one = AsyncMock(return_value=None)
    service.home_cache_service.set_one = AsyncMock()
    service.home_cache_service.cache.delete_cache = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_get_home_returns_empty_state_when_dependencies_have_no_data():
    trainer = build_trainer()
    service = build_service(trainer=trainer)

    result = await service.get_home(trainer)

    assert result.trainer.id == trainer.id
    assert result.encounters == []
    assert result.active_encounter is None
    assert result.party == []
    assert result.latest_discoveries == []


@pytest.mark.asyncio
async def test_get_home_encounters_deduplicates_pokemon_encounters_before_adding():
    trainer = build_trainer()
    shared_encounter = build_encounter(name="route-1", order=1)
    extra_encounter = build_encounter(name="route-2", order=2)
    trainer.my_pokemons = [
        SimpleNamespace(pokemon=SimpleNamespace(encounters=[shared_encounter, extra_encounter])),
        SimpleNamespace(pokemon=SimpleNamespace(encounters=[shared_encounter])),
        SimpleNamespace(pokemon=SimpleNamespace(encounters=[])),
    ]
    service = build_service(trainer=trainer)

    result = await service._get_home_encounters(trainer)

    assert [encounter.id for encounter in result] == [shared_encounter.id, extra_encounter.id]
    assert service.trainer_encounter_service.added_payload["trainer_id"] == str(trainer.id)
    assert len(service.trainer_encounter_service.added_payload["pokemon_encounters"]) == 2


@pytest.mark.asyncio
async def test_get_home_returns_cache_hit_without_querying_dependencies():
    trainer = build_trainer()
    service = build_service(trainer=trainer)
    cached = SimpleNamespace(trainer=SimpleNamespace(id="trainer-1"))
    service.home_cache_service.get_one = AsyncMock(return_value=cached)
    service.trainer_encounter_service.get_active_encounter_by_trainer_id = AsyncMock()

    result = await service.get_home(trainer)

    assert result is cached
    service.trainer_encounter_service.get_active_encounter_by_trainer_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_home_serializes_summary_payload():
    trainer = build_trainer()
    party = [build_party_entry(build_my_pokemon(trainer))]
    latest_discoveries = [build_pokedex_entry(trainer)]
    active_battle = {
        'battle_session_id': uuid4(),
        'status': 'ACTIVE',
        'turn_number': 3,
        'wild_pokemon_name': 'pikachu',
        'wild_pokemon_level': 5,
        'trainer_active_my_pokemon_id': party[0].my_pokemon.id,
        'has_active_battle': True,
    }
    service = build_service(
        trainer=trainer,
        encounter=build_encounter(),
        party=party,
        latest_discoveries=latest_discoveries,
        active_battle=active_battle,
    )

    result = await service.get_home(trainer)

    assert result.trainer.id == trainer.id
    assert result.active_encounter is not None
    assert len(result.encounters) == 1
    assert len(result.party) == 1
    assert len(result.latest_discoveries) == 1
    assert result.active_battle is not None
    assert result.active_battle.status == 'ACTIVE'
    service.home_cache_service.set_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_home_cache_deletes_expected_key():
    trainer = build_trainer()
    service = build_service(trainer=trainer)

    await service.invalidate_home_cache(str(trainer.id))

    service.home_cache_service.cache.delete_cache.assert_awaited_once()
