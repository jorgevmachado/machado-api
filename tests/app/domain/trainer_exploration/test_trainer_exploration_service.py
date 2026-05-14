from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer_exploration.schema import (
    SelectTrainerEncounterSchema,
    UpdateTrainerPartySchema,
)
from app.domain.trainer_exploration.service import TrainerExplorationService
from app.models.enums import ExplorationEventTypeEnum, RoleEnum


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
        external_image="https://example.com/pokemon.png",
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
            ),
            SimpleNamespace(
                id=uuid4(),
                pp=5,
                max_pp=5,
                deleted_at=datetime.now(timezone.utc),
                pokemon_move_id=uuid4(),
                pokemon_move=SimpleNamespace(
                    name="disabled",
                    type="normal",
                    power=0,
                    accuracy=0,
                ),
            ),
        ],
    )


def build_encounter(name="route-1", order=1, pokemons=None):
    return SimpleNamespace(
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
        pokemons=pokemons or [build_pokemon()],
    )


def build_trainer_encounter(trainer, encounter, *, is_active=False):
    return SimpleNamespace(
        id=uuid4(),
        trainer_id=trainer.id,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
        pokemon_encounter=encounter,
        trainer=trainer,
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


def build_pokedex_entry(trainer, pokemon=None, discovered_at=None):
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
        discovered_at=discovered_at or datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        pokemon=pokemon,
        trainer=trainer,
    )


class FakeTrainerService:
    def __init__(self, trainer=None):
        self.trainer = trainer

    async def get_by_user_id(self, _user_id):
        return self.trainer


class FakeRepository:
    def __init__(self, trainer):
        self.session = FakeSession()
        self.trainer = trainer
        self.encounter_catalog = []
        self.created_known_encounters = []
        self.encounters = []
        self.active_encounter = None
        self.party_entries = []
        self.owned_my_pokemons = []
        self.latest_discoveries = []
        self.created_event_payload = None
        self.soft_deleted_at = None

    async def list_encounters_for_pokemon(self, _pokemon_name):
        return self.encounter_catalog

    async def create_known_encounters(self, **kwargs):
        self.created_known_encounters.append(kwargs)
        self.encounters = [
            build_trainer_encounter(
                self.trainer,
                encounter,
                is_active=encounter.id == kwargs["active_encounter_id"],
            )
            for encounter in kwargs["encounters"]
        ]
        self.active_encounter = next(
            (entry for entry in self.encounters if entry.is_active),
            None,
        )
        return self.encounters

    async def find_trainer_encounter(self, _trainer_id, encounter_id):
        return next((entry for entry in self.encounters if entry.id == encounter_id), None)

    async def list_trainer_encounters(self, _trainer_id):
        return self.encounters

    async def find_active_trainer_encounter(self, _trainer_id):
        return self.active_encounter

    async def deactivate_all_encounters(self, _trainer_id):
        for entry in self.encounters:
            entry.is_active = False

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

    async def create_event(self, *, trainer_id, event_type, payload):
        self.created_event_payload = {
            "trainer_id": trainer_id,
            "event_type": event_type,
            "payload": payload,
        }
        return SimpleNamespace(
            id=uuid4(),
            event_type=event_type,
            created_at=datetime.now(timezone.utc),
            payload=payload,
        )

    async def list_latest_discoveries(self, _trainer_id):
        return self.latest_discoveries


def build_service(repository, trainer):
    service = TrainerExplorationService(
        repository,
        trainer_service=FakeTrainerService(trainer),
    )
    service._invalidate_cache = AsyncMock()
    service.home_cache_service.get_one = AsyncMock(return_value=None)
    service.home_cache_service.set_one = AsyncMock()
    service.encounter_cache_service.get_list = AsyncMock(return_value=None)
    service.encounter_cache_service.set_list = AsyncMock()
    service.party_cache_service.get_list = AsyncMock(return_value=None)
    service.party_cache_service.set_list = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_get_trainer_or_404_raises_when_trainer_is_missing():
    repository = FakeRepository(trainer=None)
    service = TrainerExplorationService(
        repository,
        trainer_service=FakeTrainerService(None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service._get_trainer_or_404(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_initialize_for_trainer_creates_known_encounters_and_invalidates_cache():
    trainer = build_trainer()
    first = build_encounter(name="route-2", order=2)
    second = build_encounter(name="route-1", order=1)
    repository = FakeRepository(trainer)
    repository.encounter_catalog = [first, second]
    service = build_service(repository, trainer)

    result = await service.initialize_for_trainer(
        trainer_id=trainer.id,
        starter_pokemon_name="bulbasaur",
    )

    assert len(result) == 2
    assert repository.created_known_encounters[0]["active_encounter_id"] == second.id
    assert repository.session.commits == 1
    service._invalidate_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_all_cache_keys():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = TrainerExplorationService(
        repository,
        trainer_service=FakeTrainerService(trainer),
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()
    service.encounter_cache_service.cache.delete_cache = AsyncMock()
    service.party_cache_service.cache.delete_cache = AsyncMock()

    await service._invalidate_cache(str(trainer.id))

    service.home_cache_service.cache.delete_cache.assert_awaited_once()
    service.encounter_cache_service.cache.delete_cache.assert_awaited_once()
    service.party_cache_service.cache.delete_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_encounters_returns_cache_hit_without_querying_repository():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = build_service(repository, trainer)
    cached = [SimpleNamespace(id="cached")]
    service.encounter_cache_service.get_list = AsyncMock(return_value=cached)
    repository.list_trainer_encounters = AsyncMock()

    result = await service.list_encounters(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result == cached
    repository.list_trainer_encounters.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_encounters_serializes_and_caches_repository_entries():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    repository.encounters = [
        build_trainer_encounter(trainer, build_encounter(), is_active=True)
    ]
    service = build_service(repository, trainer)

    result = await service.list_encounters(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert len(result) == 1
    assert result[0].pokemon_encounter.name == "route-1"
    service.encounter_cache_service.set_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_active_encounter_updates_the_active_flag():
    trainer = build_trainer()
    encounter_a = build_trainer_encounter(trainer, build_encounter(), is_active=True)
    encounter_b = build_trainer_encounter(trainer, build_encounter(name="route-2", order=2))
    repository = FakeRepository(trainer)
    repository.encounters = [encounter_a, encounter_b]
    repository.active_encounter = encounter_a
    service = build_service(repository, trainer)

    result = await service.select_active_encounter(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        SelectTrainerEncounterSchema(encounter_id=encounter_b.id),
    )

    assert result.id == encounter_b.id
    assert encounter_a.is_active is False
    assert encounter_b.is_active is True
    assert repository.session.commits == 1


@pytest.mark.asyncio
async def test_select_active_encounter_raises_when_reload_fails():
    trainer = build_trainer()
    encounter = build_trainer_encounter(trainer, build_encounter(), is_active=True)
    repository = FakeRepository(trainer)
    repository.encounters = [encounter]
    repository.find_trainer_encounter = AsyncMock(side_effect=[encounter, None])
    service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.select_active_encounter(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
            SelectTrainerEncounterSchema(encounter_id=encounter.id),
        )

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_select_active_encounter_raises_when_encounter_is_missing():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.select_active_encounter(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
            SelectTrainerEncounterSchema(encounter_id=uuid4()),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_party_raises_for_invalid_owned_pokemon_ids():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    repository.owned_my_pokemons = [build_my_pokemon(trainer)]
    service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_party(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
            UpdateTrainerPartySchema(my_pokemon_ids=[uuid4(), uuid4()]),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_party_replaces_active_party_and_returns_serialized_entries():
    trainer = build_trainer()
    owned = [build_my_pokemon(trainer), build_my_pokemon(trainer, build_pokemon("squirtle"))]
    repository = FakeRepository(trainer)
    repository.owned_my_pokemons = owned
    service = build_service(repository, trainer)

    result = await service.update_party(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        UpdateTrainerPartySchema(my_pokemon_ids=[owned[0].id, owned[1].id]),
    )

    assert [entry.slot for entry in result] == [1, 2]
    assert repository.soft_deleted_at is not None
    assert repository.session.commits == 1


@pytest.mark.asyncio
async def test_get_party_returns_cache_hit_without_querying_repository():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = build_service(repository, trainer)
    cached = [SimpleNamespace(id="party-cached")]
    service.party_cache_service.get_list = AsyncMock(return_value=cached)
    repository.list_active_party = AsyncMock()

    result = await service.get_party(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result == cached
    repository.list_active_party.assert_not_awaited()


@pytest.mark.asyncio
async def test_walk_raises_when_there_is_no_active_encounter():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_walk_creates_wild_pokemon_event(monkeypatch):
    trainer = build_trainer()
    pokemon = build_pokemon("pikachu")
    active_encounter = build_trainer_encounter(
        trainer,
        build_encounter(pokemons=[pokemon]),
        is_active=True,
    )
    repository = FakeRepository(trainer)
    repository.active_encounter = active_encounter
    service = build_service(repository, trainer)
    monkeypatch.setattr(
        "app.domain.trainer_exploration.service.choose_event_type",
        lambda: ExplorationEventTypeEnum.WILD_POKEMON,
    )
    monkeypatch.setattr(
        "app.domain.trainer_exploration.service.choose_wild_pokemon",
        lambda _pokemons: pokemon,
    )

    result = await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result.event_type == ExplorationEventTypeEnum.WILD_POKEMON
    assert result.pokemon.name == "pikachu"
    assert repository.created_event_payload["payload"]["pokemon_id"] == str(pokemon.id)
    assert repository.session.commits == 1


@pytest.mark.asyncio
async def test_walk_creates_pokeball_event_and_updates_trainer_inventory(monkeypatch):
    trainer = build_trainer()
    active_encounter = build_trainer_encounter(trainer, build_encounter(), is_active=True)
    repository = FakeRepository(trainer)
    repository.active_encounter = active_encounter
    service = build_service(repository, trainer)
    monkeypatch.setattr(
        "app.domain.trainer_exploration.service.choose_event_type",
        lambda: ExplorationEventTypeEnum.POKEBALLS,
    )
    monkeypatch.setattr(
        "app.domain.trainer_exploration.service.build_pokeball_reward",
        lambda: 2,
    )

    result = await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result.event_type == ExplorationEventTypeEnum.POKEBALLS
    assert result.pokeballs_found == 2
    assert result.trainer_pokeballs == 5
    assert trainer.pokeballs == 5


@pytest.mark.asyncio
async def test_get_home_returns_cache_hit_without_querying_repository():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = build_service(repository, trainer)
    cached = SimpleNamespace(trainer=SimpleNamespace(id="trainer-1"))
    service.home_cache_service.get_one = AsyncMock(return_value=cached)
    repository.find_active_trainer_encounter = AsyncMock()

    result = await service.get_home(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result is cached
    repository.find_active_trainer_encounter.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_home_serializes_summary_payload():
    trainer = build_trainer()
    my_pokemon = build_my_pokemon(trainer)
    repository = FakeRepository(trainer)
    repository.active_encounter = build_trainer_encounter(
        trainer,
        build_encounter(),
        is_active=True,
    )
    repository.party_entries = [build_party_entry(my_pokemon)]
    repository.latest_discoveries = [build_pokedex_entry(trainer)]
    service = build_service(repository, trainer)

    result = await service.get_home(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result.trainer.id == trainer.id
    assert result.active_encounter is not None
    assert len(result.party) == 1
    assert result.party[0].my_pokemon.moves[0].pokemon_move_name == "tackle"
    assert len(result.latest_discoveries) == 1
    service.home_cache_service.set_one.assert_awaited_once()
