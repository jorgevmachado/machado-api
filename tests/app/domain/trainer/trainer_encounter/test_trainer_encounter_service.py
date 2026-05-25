from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.encounter import (
    SelectTrainerEncounterSchema,
    TrainerEncounterService,
)
from app.models.enums import ExplorationEventTypeEnum, PokemonStatusEnum, RoleEnum


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


class FakeTrainerService:
    def __init__(self, trainer=None):
        self.trainer = trainer
        self.invalidate_home_cache = AsyncMock()

    async def get_by_user_id(self, _user_id):
        return self.trainer


class FakeBattleSessionService:
    def __init__(self):
        self.active = False
        self.created = None

    async def has_active_battle(self, _trainer_id):
        return self.active

    async def create_or_resume_battle(self, *, trainer, exploration_event, wild_pokemon):
        self.created = {
            "trainer": trainer,
            "exploration_event": exploration_event,
            "wild_pokemon": wild_pokemon,
        }
        return SimpleNamespace(
            id=uuid4(),
            status="ACTIVE",
        )


class FakeRepository:
    def __init__(self, trainer):
        self.session = FakeSession()
        self.trainer = trainer
        self.encounter_catalog = []
        self.created_known_encounters = []
        self.encounters = []
        self.active_encounter = None
        self.created_event_payload = None

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

    async def find_by(self, **kwargs):
        if kwargs.get("is_active") is True:
            return await self.find_active_trainer_encounter(kwargs.get("trainer_id"))
        if kwargs.get("pokemon_encounter_id") is not None:
            return next(
                (
                    entry for entry in self.encounters
                    if entry.pokemon_encounter.id == kwargs["pokemon_encounter_id"]
                ),
                None,
            )
        return await self.find_trainer_encounter(
            kwargs.get("trainer_id"),
            kwargs.get("id"),
        )

    async def list_all(self, page_filter=None):
        trainer_id = getattr(page_filter, "trainer_id", None) if page_filter else None
        return await self.list_trainer_encounters(trainer_id)

    async def find_active_trainer_encounter(self, _trainer_id):
        return self.active_encounter

    async def deactivate_all_encounters(self, _trainer_id):
        for entry in self.encounters:
            entry.is_active = False

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

    async def save(self, entity):
        persisted = build_trainer_encounter(
            self.trainer,
            next(
                encounter
                for encounter in self.encounter_catalog
                if encounter.id == entity.pokemon_encounter_id
            ),
            is_active=entity.is_active,
        )
        persisted.id = uuid4()
        self.encounters.append(persisted)
        return persisted


def build_service(repository, trainer, battle_service=None):
    trainer_service = FakeTrainerService(trainer)
    service = TrainerEncounterService(
        repository,
        trainer_service=trainer_service,
        battle_session_service=battle_service or FakeBattleSessionService(),
    )
    service._invalidate_cache = AsyncMock()
    service.encounter_cache_service.get_list = AsyncMock(return_value=None)
    service.encounter_cache_service.set_list = AsyncMock()
    return service, trainer_service


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_encounter_cache_key():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service = TrainerEncounterService(
        repository,
        trainer_service=FakeTrainerService(trainer),
    )
    service.encounter_cache_service.cache.delete_cache = AsyncMock()

    await service._invalidate_cache(str(trainer.id))

    service.encounter_cache_service.cache.delete_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trainer_or_404_raises_when_trainer_is_missing():
    repository = FakeRepository(trainer=None)
    service = TrainerEncounterService(
        repository,
        trainer_service=FakeTrainerService(None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service._get_trainer_or_404(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_initialize_for_trainer_creates_known_encounters_and_invalidates_caches():
    trainer = build_trainer()
    first = build_encounter(name="route-2", order=2)
    second = build_encounter(name="route-1", order=1)
    repository = FakeRepository(trainer)
    repository.encounter_catalog = [first, second]
    service, trainer_service = build_service(repository, trainer)

    result = await service.initialize_for_trainer(
        trainer_id=trainer.id,
        starter_pokemon_name="bulbasaur",
    )

    assert len(result) == 2
    assert repository.created_known_encounters[0]["active_encounter_id"] == second.id
    assert repository.session.commits == 1
    service._invalidate_cache.assert_awaited_once()
    trainer_service.invalidate_home_cache.assert_awaited_once_with(str(trainer.id))


@pytest.mark.asyncio
async def test_add_encounters_reuses_existing_entries_and_persists_missing_ones():
    trainer = build_trainer()
    first = build_encounter(name="route-1", order=1)
    second = build_encounter(name="route-2", order=2)
    repository = FakeRepository(trainer)
    repository.encounter_catalog = [first, second]
    existing = build_trainer_encounter(trainer, first, is_active=True)
    repository.encounters = [existing]
    service, _trainer_service = build_service(repository, trainer)

    result = await service.add_encounters(str(trainer.id), [first, second])

    assert result[0] is existing
    assert result[1].pokemon_encounter.id == second.id
    assert len(repository.encounters) == 2


@pytest.mark.asyncio
async def test_list_encounters_returns_cache_hit_without_querying_repository():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service, _trainer_service = build_service(repository, trainer)
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
    service, _trainer_service = build_service(repository, trainer)

    result = await service.list_encounters(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert len(result) == 1
    assert result[0].pokemon_encounter.name == "route-1"
    service.encounter_cache_service.set_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_active_encounter_updates_the_active_flag_and_invalidates_home():
    trainer = build_trainer()
    encounter_a = build_trainer_encounter(trainer, build_encounter(), is_active=True)
    encounter_b = build_trainer_encounter(trainer, build_encounter(name="route-2", order=2))
    repository = FakeRepository(trainer)
    repository.encounters = [encounter_a, encounter_b]
    repository.active_encounter = encounter_a
    service, trainer_service = build_service(repository, trainer)

    result = await service.select_active_encounter(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        SelectTrainerEncounterSchema(encounter_id=encounter_b.id),
    )

    assert result.id == encounter_b.id
    assert encounter_a.is_active is False
    assert encounter_b.is_active is True
    assert repository.session.commits == 1
    trainer_service.invalidate_home_cache.assert_awaited_once_with(str(trainer.id))


@pytest.mark.asyncio
async def test_select_active_encounter_raises_when_reload_fails():
    trainer = build_trainer()
    encounter = build_trainer_encounter(trainer, build_encounter(), is_active=True)
    repository = FakeRepository(trainer)
    repository.encounters = [encounter]
    repository.find_trainer_encounter = AsyncMock(side_effect=[encounter, None])
    service, _trainer_service = build_service(repository, trainer)

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
    service, _trainer_service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.select_active_encounter(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
            SelectTrainerEncounterSchema(encounter_id=uuid4()),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_walk_raises_when_there_is_no_active_encounter():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service, _trainer_service = build_service(repository, trainer)

    with pytest.raises(HTTPException) as exc_info:
        await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_walk_raises_when_trainer_has_active_battle():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    battle_service = FakeBattleSessionService()
    battle_service.active = True
    service, _trainer_service = build_service(repository, trainer, battle_service=battle_service)

    with pytest.raises(HTTPException) as exc_info:
        await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert exc_info.value.status_code == 409


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
    battle_service = FakeBattleSessionService()
    service, trainer_service = build_service(
        repository,
        trainer,
        battle_service=battle_service,
    )
    monkeypatch.setattr(
        "app.domain.trainer.encounter.service.choose_event_type",
        lambda: ExplorationEventTypeEnum.WILD_POKEMON,
    )
    monkeypatch.setattr(
        "app.domain.trainer.encounter.service.choose_wild_pokemon",
        lambda _pokemons: pokemon,
    )

    result = await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result.event_type == ExplorationEventTypeEnum.WILD_POKEMON
    assert result.pokemon.name == "pikachu"
    assert repository.created_event_payload["payload"]["pokemon_id"] == str(pokemon.id)
    assert result.has_active_battle is True
    assert result.battle_session_id is not None
    assert result.battle_status == "ACTIVE"
    assert repository.session.commits == 1
    assert battle_service.created is not None
    trainer_service.invalidate_home_cache.assert_awaited_once_with(str(trainer.id))


@pytest.mark.asyncio
async def test_walk_creates_pokeball_event_and_updates_trainer_inventory(monkeypatch):
    trainer = build_trainer()
    active_encounter = build_trainer_encounter(trainer, build_encounter(), is_active=True)
    repository = FakeRepository(trainer)
    repository.active_encounter = active_encounter
    service, _trainer_service = build_service(repository, trainer)
    monkeypatch.setattr(
        "app.domain.trainer.encounter.service.choose_event_type",
        lambda: ExplorationEventTypeEnum.POKEBALLS,
    )
    monkeypatch.setattr(
        "app.domain.trainer.encounter.service.build_pokeball_reward",
        lambda: 2,
    )

    result = await service.walk(SimpleNamespace(id=uuid4(), role=RoleEnum.USER))

    assert result.event_type == ExplorationEventTypeEnum.POKEBALLS
    assert result.pokeballs_found == 2
    assert result.trainer_pokeballs == 5
    assert trainer.pokeballs == 5


@pytest.mark.asyncio
async def test_get_active_encounter_by_trainer_id_returns_none_when_missing():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    service, _trainer_service = build_service(repository, trainer)

    result = await service.get_active_encounter_by_trainer_id(trainer.id)

    assert result is None


@pytest.mark.asyncio
async def test_get_active_encounter_by_trainer_id_serializes_active_encounter():
    trainer = build_trainer()
    repository = FakeRepository(trainer)
    repository.active_encounter = build_trainer_encounter(
        trainer,
        build_encounter(),
        is_active=True,
    )
    service, _trainer_service = build_service(repository, trainer)

    result = await service.get_active_encounter_by_trainer_id(trainer.id)

    assert result is not None
    assert result.pokemon_encounter.name == "route-1"
