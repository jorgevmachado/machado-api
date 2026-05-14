from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.my_pokemon.schema import MyPokemonSchema
from app.domain.pokedex.schema import PokedexSchema
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingEncounterSchema,
)
from app.domain.trainer.service import TrainerService
from app.models.enums import RoleEnum


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

    async def initialize_for_trainer(self, **kwargs):
        self.created_payload = kwargs
        return self.entities

    def to_schema(self, entity):
        return PokedexSchema.model_validate(entity)


class FakeTrainerExplorationService:
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


@pytest.mark.asyncio
async def test_get_by_user_id_delegates_to_repository():
    trainer = SimpleNamespace(id=uuid4())
    repository = FakeTrainerRepository(trainer=trainer)
    service = TrainerService(
        repository,
        FakeMyPokemonService(),
        FakePokedexService(),
        FakeTrainerExplorationService(),
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
        FakeTrainerExplorationService(),
    )
    user_id = uuid4()

    result = await service.create(user_id=user_id, pokeballs=5, capture_rate=45)

    assert result.user_id == user_id
    assert repository.created_payload == {
        "user_id": user_id,
        "pokeballs": 5,
        "capture_rate": 45,
    }


@pytest.mark.asyncio
async def test_onboard_creates_trainer_and_owned_pokemon_for_user():
    repository = FakeTrainerRepository()
    my_pokemon_service = FakeMyPokemonService()
    pokedex_service = FakePokedexService()
    trainer_exploration_service = FakeTrainerExplorationService()
    service = TrainerService(
        repository,
        my_pokemon_service,
        pokedex_service,
        trainer_exploration_service,
    )

    result = await service.onboard(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        OnboardingTrainerSchema(pokemon_name=" bulbasaur ", nickname="Leaf"),
    )

    assert repository.created_payload is not None
    assert repository.created_payload["pokeballs"] == 1
    assert repository.created_payload["capture_rate"] == 75
    assert my_pokemon_service.created_payload["pokemon_name"] == "bulbasaur"
    assert my_pokemon_service.created_payload["nickname"] == "Leaf"
    assert my_pokemon_service.created_payload["commit"] is False
    assert pokedex_service.created_payload["trainer_id"] is not None
    assert pokedex_service.created_payload["discovered_pokemon_name"] == "bulbasaur"
    assert pokedex_service.created_payload["commit"] is False
    assert trainer_exploration_service.created_payload["trainer_id"] is not None
    assert trainer_exploration_service.created_payload["starter_pokemon_name"] == "bulbasaur"
    assert trainer_exploration_service.created_payload["commit"] is False
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
        FakeTrainerExplorationService(),
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
