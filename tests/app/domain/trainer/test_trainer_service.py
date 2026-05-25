from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.my_pokemon import MyPokemonSchema
from app.domain.trainer.battle.schema import CaptureBattlePokemonSchema
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingEncounterSchema,
)
from app.domain.trainer.service import TrainerService
from app.models.enums import BattleSessionStatusEnum, RoleEnum


class FakeSession:
    def __init__(self, repository):
        self.repository = repository
        self.committed = False
        self.rolled_back = False
        self.pending_entity = None

    def add(self, entity):
        self.pending_entity = entity

    async def flush(self):
        if self.pending_entity is not None:
            self.repository.created_payload = {
                "user_id": self.pending_entity.user_id,
                "pokeballs": self.pending_entity.pokeballs,
                "capture_rate": self.pending_entity.capture_rate,
                "base_capture_rate": self.pending_entity.base_capture_rate,
                "capture_progress_points": self.pending_entity.capture_progress_points,
            }
            self.pending_entity.id = uuid4()
            self.repository.trainer = self.pending_entity

    async def refresh(self, _entity):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class FakeTrainerRepository:
    def __init__(self, trainer=None):
        self.session = FakeSession(self)
        self.trainer = trainer
        self.created_payload = None

    async def find_by(self, **kwargs):
        return self.trainer


class FakeMyPokemonService:
    def __init__(self):
        self.created_payload = None
        trainer_id = uuid4()
        self.entity = SimpleNamespace(
            id=uuid4(),
            name="bulbasaur",
            nickname="Leaf",
            level=1,
            experience=0,
            hp=45,
            max_hp=45,
            attack=49,
            defense=49,
            special_attack=65,
            special_defense=65,
            speed=45,
            captured_at=datetime.now(timezone.utc),
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
            moves=[],
        )

    async def create_owned_for_trainer(self, **kwargs):
        self.created_payload = kwargs
        return self.entity

    def to_schema(self, entity):
        return MyPokemonSchema.model_validate(entity)


class FakePokedexService:
    def __init__(self):
        trainer_id = uuid4()
        self.created_payload = None
        self.entities = [
            SimpleNamespace(
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
                pokemon=SimpleNamespace(
                    id=uuid4(),
                    name="bulbasaur",
                    order=1,
                    hp=45,
                    speed=45,
                    height=7,
                    weight=69,
                    status='COMPLETE',
                    attack=49,
                    defense=49,
                    is_baby=False,
                    gender_rate=1,
                    is_mythical=False,
                    is_legendary=False,
                    capture_rate=45,
                    hatch_counter=20,
                    base_happiness=50,
                    special_attack=65,
                    special_defense=65,
                    base_experience=64,
                    has_gender_differences=False,
                    created_at=datetime.now(timezone.utc),
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
        ]
        self.is_discovered = AsyncMock(return_value=False)
        self.discover = AsyncMock(return_value=self.entities[0])

    async def initialize_for_trainer(self, **kwargs):
        self.created_payload = kwargs
        return self.entities

    def to_schema(self, entity):
        return PokedexSchema.model_validate(entity)


class FakeTrainerEncounterService:
    def __init__(self):
        self.created_payload = None
        self.entities = [
            SimpleNamespace(
                id=uuid4(),
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=None,
                deleted_at=None,
                pokemon_encounter=SimpleNamespace(
                    id=uuid4(),
                    url="https://example.com/encounters/1",
                    name="route-1",
                    order=1,
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
                ),
            )
        ]

    async def initialize_for_trainer(self, **kwargs):
        self.created_payload = kwargs
        return self.entities

    def to_encounter_schema(self, entity):
        return TrainerOnboardingEncounterSchema.model_validate(entity)


class FakeBattleSessionRepository:
    def __init__(self, active_session=None, latest_session=None):
        self.find_active_by_trainer_id = AsyncMock(return_value=active_session)
        self.find_latest_by_trainer_id = AsyncMock(return_value=latest_session)


class FakeBattleSessionService:
    def __init__(self, active_session=None, latest_session=None):
        self.repository = FakeBattleSessionRepository(active_session, latest_session)
        self.calculate_capture_chance = Mock(return_value=64)
        self.rolled_capture_success = Mock(return_value=True)
        self.create_ineligible_capture_result = AsyncMock(return_value="ineligible")
        self.process_capture_failure = AsyncMock(return_value="failed")
        self.finalize_capture_success = AsyncMock(return_value="captured")


@pytest.mark.asyncio
async def test_get_by_user_id_delegates_to_repository():
    trainer = SimpleNamespace(id=uuid4())
    repository = FakeTrainerRepository(trainer=trainer)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
    )

    result = await service.get_by_user_id(uuid4())

    assert result is trainer


@pytest.mark.asyncio
async def test_create_delegates_to_repository():
    repository = FakeTrainerRepository()
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
    )
    user_id = uuid4()

    result = await service.create(user_id=user_id, pokeballs=5, capture_rate=45)

    assert result.user_id == user_id
    assert repository.created_payload == {
        "user_id": user_id,
        "pokeballs": 5,
        "capture_rate": 45,
        "base_capture_rate": 45,
        "capture_progress_points": 0,
    }


@pytest.mark.asyncio
async def test_onboard_creates_trainer_and_owned_pokemon_for_user():
    repository = FakeTrainerRepository()
    my_pokemon_service = FakeMyPokemonService()
    pokedex_service = FakePokedexService()
    trainer_encounter_service = FakeTrainerEncounterService()
    service = TrainerService(
        repository,
        my_pokemon_service,
        pokedex_service,
        trainer_encounter_service,
    )

    result = await service.onboard(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        OnboardingTrainerSchema(pokemon_name=" bulbasaur ", nickname="Leaf"),
    )

    assert repository.created_payload is not None
    assert repository.created_payload["pokeballs"] == 1
    assert repository.created_payload["capture_rate"] == 75
    assert repository.created_payload["base_capture_rate"] == 75
    assert repository.created_payload["capture_progress_points"] == 0
    assert my_pokemon_service.created_payload["pokemon_name"] == "bulbasaur"
    assert my_pokemon_service.created_payload["nickname"] == "Leaf"
    assert my_pokemon_service.created_payload["commit"] is False
    assert pokedex_service.created_payload["trainer_id"] is not None
    assert pokedex_service.created_payload["discovered_pokemon_name"] == "bulbasaur"
    assert pokedex_service.created_payload["commit"] is False
    assert trainer_encounter_service.created_payload["trainer_id"] is not None
    assert trainer_encounter_service.created_payload["starter_pokemon_name"] == "bulbasaur"
    assert trainer_encounter_service.created_payload["commit"] is False
    assert repository.session.committed is True
    assert result.user_id is not None
    assert len(result.my_pokemons) == 1
    assert len(result.pokedex) == 1
    assert len(result.known_encounters) == 1
    assert result.my_pokemons[0].nickname == "Leaf"


@pytest.mark.asyncio
async def test_onboard_uses_admin_values_when_role_is_admin():
    repository = FakeTrainerRepository()
    my_pokemon_service = FakeMyPokemonService()
    service = TrainerService(
        repository,
        my_pokemon_service,
        FakePokedexService(),
        FakeTrainerEncounterService(),
    )

    await service.onboard(
        SimpleNamespace(id=uuid4(), role=RoleEnum.ADMIN),
        OnboardingTrainerSchema(
            pokemon_name="bulbasaur",
            nickname="Leaf",
            pokeballs=8,
            capture_rate=75,
        ),
    )

    assert repository.created_payload["pokeballs"] == 8
    assert repository.created_payload["capture_rate"] == 75


@pytest.mark.asyncio
async def test_onboard_rejects_invalid_non_admin_starter():
    repository = FakeTrainerRepository()
    service = TrainerService(repository, FakeMyPokemonService(), FakePokedexService())

    with pytest.raises(HTTPException) as exc_info:
        await service.onboard(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
            OnboardingTrainerSchema(pokemon_name="pikachu"),
        )

    assert exc_info.value.status_code == 400
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_onboard_rejects_when_trainer_already_exists():
    repository = FakeTrainerRepository(trainer=SimpleNamespace(id=uuid4()))
    service = TrainerService(repository, FakeMyPokemonService(), FakePokedexService())

    with pytest.raises(HTTPException) as exc_info:
        await service.onboard(
            SimpleNamespace(id=uuid4(), role=RoleEnum.ADMIN),
            OnboardingTrainerSchema(pokemon_name="bulbasaur"),
        )

    assert exc_info.value.status_code == 409
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_onboard_rolls_back_when_owned_pokemon_creation_fails():
    repository = FakeTrainerRepository()
    my_pokemon_service = FakeMyPokemonService()
    my_pokemon_service.create_owned_for_trainer = AsyncMock(
        side_effect=RuntimeError("boom")
    )
    service = TrainerService(repository, my_pokemon_service, FakePokedexService())

    with pytest.raises(HTTPException) as exc_info:
        await service.onboard(
            SimpleNamespace(id=uuid4(), role=RoleEnum.ADMIN),
            OnboardingTrainerSchema(pokemon_name="bulbasaur"),
        )

    assert exc_info.value.status_code == 500
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_capture_battle_pokemon_success_updates_progression_and_commits():
    trainer = SimpleNamespace(
        id=uuid4(),
        pokeballs=3,
        capture_rate=75,
        base_capture_rate=75,
        capture_progress_points=0,
    )
    battle_session = SimpleNamespace(
        id=uuid4(),
        wild_pokemon_name="pikachu",
        wild_pokemon_snapshot={"capture_rate": 45, "current_hp": 5, "max_hp": 20},
        status=BattleSessionStatusEnum.ACTIVE,
    )
    repository = FakeTrainerRepository(trainer=trainer)
    my_pokemon_service = FakeMyPokemonService()
    pokedex_service = FakePokedexService()
    pokedex_service.is_discovered = AsyncMock(return_value=False)
    pokedex_service.discover = AsyncMock(return_value=SimpleNamespace())
    battle_service = FakeBattleSessionService(active_session=battle_session)
    service = TrainerService(
        repository,
        my_pokemon_service,
        pokedex_service,
        FakeTrainerEncounterService(),
        battle_session_service=battle_service,
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()

    result = await service.capture_battle_pokemon(
        trainer,
        CaptureBattlePokemonSchema(nickname="Spark"),
    )

    assert result == "captured"
    assert trainer.pokeballs == 2
    assert trainer.capture_progress_points == 2
    assert trainer.capture_rate == 77
    assert my_pokemon_service.created_payload["pokemon_name"] == "pikachu"
    assert my_pokemon_service.created_payload["nickname"] == "Spark"
    assert my_pokemon_service.created_payload["commit"] is False
    assert pokedex_service.discover.await_count == 1
    assert repository.session.committed is True


@pytest.mark.asyncio
async def test_capture_battle_pokemon_rejects_ineligible_but_consumes_pokeball():
    trainer = SimpleNamespace(
        id=uuid4(),
        pokeballs=2,
        capture_rate=40,
        base_capture_rate=40,
        capture_progress_points=0,
    )
    battle_session = SimpleNamespace(
        id=uuid4(),
        wild_pokemon_name="pikachu",
        wild_pokemon_snapshot={"capture_rate": 45, "current_hp": 5, "max_hp": 20},
        status=BattleSessionStatusEnum.ACTIVE,
    )
    repository = FakeTrainerRepository(trainer=trainer)
    battle_service = FakeBattleSessionService(active_session=battle_session)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
        battle_session_service=battle_service,
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()

    result = await service.capture_battle_pokemon(trainer, CaptureBattlePokemonSchema())

    assert result == "ineligible"
    assert trainer.pokeballs == 1
    assert trainer.capture_progress_points == 0
    battle_service.process_capture_failure.assert_not_called()
    battle_service.finalize_capture_success.assert_not_called()
    assert repository.session.committed is True


@pytest.mark.asyncio
async def test_capture_battle_pokemon_failed_chance_does_not_progress_trainer():
    trainer = SimpleNamespace(
        id=uuid4(),
        pokeballs=2,
        capture_rate=75,
        base_capture_rate=75,
        capture_progress_points=0,
    )
    battle_session = SimpleNamespace(
        id=uuid4(),
        wild_pokemon_name="pikachu",
        wild_pokemon_snapshot={"capture_rate": 45, "current_hp": 10, "max_hp": 20},
        status=BattleSessionStatusEnum.ACTIVE,
    )
    repository = FakeTrainerRepository(trainer=trainer)
    battle_service = FakeBattleSessionService(active_session=battle_session)
    battle_service.rolled_capture_success = Mock(return_value=False)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
        battle_session_service=battle_service,
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()

    result = await service.capture_battle_pokemon(trainer, CaptureBattlePokemonSchema())

    assert result == "failed"
    assert trainer.pokeballs == 1
    assert trainer.capture_progress_points == 0
    assert trainer.capture_rate == 75
    battle_service.process_capture_failure.assert_awaited_once()
    assert repository.session.committed is True


@pytest.mark.asyncio
async def test_capture_battle_pokemon_rejects_without_pokeballs():
    trainer = SimpleNamespace(
        id=uuid4(),
        pokeballs=0,
        capture_rate=75,
        base_capture_rate=75,
        capture_progress_points=0,
    )
    battle_session = SimpleNamespace(
        id=uuid4(),
        wild_pokemon_name="pikachu",
        wild_pokemon_snapshot={"capture_rate": 45, "current_hp": 10, "max_hp": 20},
        status=BattleSessionStatusEnum.ACTIVE,
    )
    repository = FakeTrainerRepository(trainer=trainer)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
        battle_session_service=FakeBattleSessionService(active_session=battle_session),
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await service.capture_battle_pokemon(trainer, CaptureBattlePokemonSchema())

    assert exc_info.value.status_code == 400
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_capture_battle_pokemon_rejects_when_latest_battle_was_already_captured():
    trainer = SimpleNamespace(
        id=uuid4(),
        pokeballs=2,
        capture_rate=75,
        base_capture_rate=75,
        capture_progress_points=0,
    )
    repository = FakeTrainerRepository(trainer=trainer)
    latest_battle = SimpleNamespace(status=BattleSessionStatusEnum.CAPTURED)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
        battle_session_service=FakeBattleSessionService(active_session=None, latest_session=latest_battle),
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await service.capture_battle_pokemon(trainer, CaptureBattlePokemonSchema())

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_capture_battle_pokemon_rejects_when_trainer_has_no_active_battle():
    trainer = SimpleNamespace(
        id=uuid4(),
        pokeballs=2,
        capture_rate=75,
        base_capture_rate=75,
        capture_progress_points=0,
    )
    repository = FakeTrainerRepository(trainer=trainer)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerEncounterService(),
        battle_session_service=FakeBattleSessionService(active_session=None, latest_session=None),
    )
    service.home_cache_service.cache.delete_cache = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await service.capture_battle_pokemon(trainer, CaptureBattlePokemonSchema())

    assert exc_info.value.status_code == 404


def test_calculate_effective_capture_rate_uses_hybrid_progression():
    result = TrainerService.calculate_effective_capture_rate(
        base_capture_rate=75,
        capture_progress_points=40,
    )

    assert result == 94


@pytest.mark.asyncio
async def test_onboard_rolls_back_when_pokedex_initialization_fails():
    repository = FakeTrainerRepository()
    pokedex_service = FakePokedexService()
    pokedex_service.initialize_for_trainer = AsyncMock(side_effect=RuntimeError("boom"))
    service = TrainerService(repository, FakeMyPokemonService(), pokedex_service)

    with pytest.raises(HTTPException) as exc_info:
        await service.onboard(
            SimpleNamespace(id=uuid4(), role=RoleEnum.ADMIN),
            OnboardingTrainerSchema(pokemon_name="bulbasaur"),
        )

    assert exc_info.value.status_code == 500
    assert repository.session.rolled_back is True
