from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.my_pokemon.schema import CreateMyPokemonSchema
from app.domain.trainer.my_pokemon.service import MyPokemonService


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.refreshed = []

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, entity):
        self.refreshed.append(entity)


class FakeTrainerService:
    def __init__(self, trainer=None):
        self.trainer = trainer

    async def get_by_user_id(self, _user_id):
        return self.trainer


class FakeRepository:
    def __init__(self, *, base_pokemon=None, existing_names=None):
        self.session = FakeSession()
        self.base_pokemon = base_pokemon
        self.existing_names = existing_names or set()
        self.created_payload = None
        self.attached_moves = []
        self.created_entity = None

    async def find_base_pokemon(self, _pokemon_name):
        return self.base_pokemon

    async def list_existing_owned_names(self, _trainer_id):
        return self.existing_names

    async def create_owned(self, **kwargs):
        self.created_payload = kwargs
        self.created_entity = SimpleNamespace(
            id=uuid4(),
            name=kwargs["name"],
            nickname=kwargs["nickname"],
            level=kwargs["attributes"]["level"],
            experience=kwargs["attributes"]["experience"],
            hp=kwargs["attributes"]["hp"],
            max_hp=kwargs["attributes"]["max_hp"],
            attack=kwargs["attributes"]["attack"],
            defense=kwargs["attributes"]["defense"],
            special_attack=kwargs["attributes"]["special_attack"],
            special_defense=kwargs["attributes"]["special_defense"],
            speed=kwargs["attributes"]["speed"],
            captured_at="2026-05-12T00:00:00Z",
            created_at="2026-05-12T00:00:00Z",
            updated_at=None,
            pokemon=self.base_pokemon,
            trainer=SimpleNamespace(
                id=kwargs["trainer_id"],
                user_id=uuid4(),
                pokeballs=1,
                capture_rate=75,
            ),
            moves=[],
        )
        return self.created_entity

    async def attach_moves(self, *, my_pokemon_id, moves):
        self.attached_moves = [
            SimpleNamespace(
                id=uuid4(),
                pp=move.pp,
                max_pp=move.pp,
                pokemon_move_id=move.id,
                pokemon_move=move,
                deleted_at=None,
            )
            for move in moves
        ]
        self.created_entity.moves = self.attached_moves

    async def find_owned_detail(self, _trainer_id, _name):
        return self.created_entity

    async def list_owned(self, _trainer_id, _page_filter=None):
        return [self.created_entity] if self.created_entity else []

    async def find_by(self, **kwargs):
        return await self.find_owned_detail(
            kwargs.get("trainer_id"),
            kwargs.get("name"),
        )

    async def list_all(self, page_filter=None):
        trainer_id = getattr(page_filter, "trainer_id", None) if page_filter else None
        return await self.list_owned(trainer_id, page_filter)


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
        moves=[
            SimpleNamespace(
                id=uuid4(),
                name="tackle",
                type="normal",
                power=40,
                accuracy=100,
                pp=35,
                deleted_at=None,
            ),
            SimpleNamespace(
                id=uuid4(),
                name="growl",
                type="normal",
                power=0,
                accuracy=100,
                pp=40,
                deleted_at=None,
            ),
        ],
        deleted_at=None,
    )


def test_service_init_builds_default_dependencies_from_session():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer_service_instance = SimpleNamespace(name="trainer-service")
    pokemon_service_instance = SimpleNamespace(name="pokemon-service")
    move_service_instance = SimpleNamespace(name="move-service")

    with (
        patch(
            "app.domain.trainer.service.TrainerService.from_session",
            return_value=trainer_service_instance,
        ) as trainer_factory,
        patch(
            "app.domain.pokemon.service.PokemonService.from_session",
            return_value=pokemon_service_instance,
        ) as pokemon_factory,
        patch(
            "app.domain.trainer.my_pokemon.move.service.MyPokemonMoveService.from_session",
            return_value=move_service_instance,
        ) as move_factory,
    ):
        service = MyPokemonService(repository=repository)

    trainer_factory.assert_called_once_with(repository.session)
    pokemon_factory.assert_called_once_with(repository.session)
    move_factory.assert_called_once_with(repository.session)
    assert service.trainer_service is trainer_service_instance
    assert service.pokemon_service is pokemon_service_instance
    assert service.my_pokemon_move_service is move_service_instance


@pytest.mark.asyncio
async def test_create_delegates_to_create_owned_for_trainer():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer_service = FakeTrainerService()
    pokemon_service = AsyncMock()
    my_pokemon_move_service = AsyncMock()
    service = MyPokemonService(
        repository=repository,
        trainer_service=trainer_service,
        pokemon_service=pokemon_service,
        my_pokemon_move_service=my_pokemon_move_service,
    )
    service.create_owned_for_trainer = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    trainer = SimpleNamespace(id=uuid4())
    payload = CreateMyPokemonSchema(pokemon_name="bulbasaur", nickname="Buba")

    await service.create(trainer=trainer, payload=payload)

    service.create_owned_for_trainer.assert_awaited_once_with(
        trainer_id=trainer.id,
        pokemon_name="bulbasaur",
        nickname="Buba",
    )


@pytest.mark.asyncio
async def test_create_owned_for_trainer_returns_fresh_and_commits():
    trainer_id = uuid4()
    base_pokemon = build_base_pokemon()
    repository = FakeRepository(base_pokemon=base_pokemon)
    trainer_service = FakeTrainerService()
    pokemon_service = AsyncMock()
    pokemon_service.find_detail.return_value = base_pokemon
    my_pokemon_move_service = AsyncMock()
    fresh = SimpleNamespace(id=uuid4(), name="bulbasaur")
    repository.find_by = AsyncMock(return_value=fresh)
    repository.save = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid4(),
            name="bulbasaur",
        )
    )
    service = MyPokemonService(
        repository=repository,
        trainer_service=trainer_service,
        pokemon_service=pokemon_service,
        my_pokemon_move_service=my_pokemon_move_service,
    )
    service.list_all = AsyncMock(return_value=set())
    service._invalidate_cache = AsyncMock()

    result = await service.create_owned_for_trainer(
        trainer_id=trainer_id,
        pokemon_name="  bulbasaur  ",
        nickname="  ",
    )

    assert result is fresh
    pokemon_service.find_detail.assert_awaited_once_with(identifier="bulbasaur")
    my_pokemon_move_service.sync_from_resources.assert_awaited_once()
    assert repository.session.committed is True
    assert len(repository.session.refreshed) == 1
    service._invalidate_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_owned_for_trainer_raises_not_found_when_base_pokemon_is_missing():
    repository = FakeRepository(base_pokemon=None)
    trainer_service = FakeTrainerService()
    pokemon_service = AsyncMock()
    pokemon_service.find_detail.return_value = None
    my_pokemon_move_service = AsyncMock()
    service = MyPokemonService(
        repository=repository,
        trainer_service=trainer_service,
        pokemon_service=pokemon_service,
        my_pokemon_move_service=my_pokemon_move_service,
    )

    with pytest.raises(HTTPException) as error:
        await service.create_owned_for_trainer(
            trainer_id=uuid4(),
            pokemon_name="missingno",
            nickname=None,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Pokemon not found"
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_create_owned_for_trainer_rolls_back_when_fresh_entity_is_missing():
    trainer_id = uuid4()
    base_pokemon = build_base_pokemon()
    repository = FakeRepository(base_pokemon=base_pokemon)
    trainer_service = FakeTrainerService()
    pokemon_service = AsyncMock()
    pokemon_service.find_detail.return_value = base_pokemon
    my_pokemon_move_service = AsyncMock()
    repository.save = AsyncMock(return_value=SimpleNamespace(id=uuid4(), name="bulbasaur"))
    repository.find_by = AsyncMock(return_value=None)
    service = MyPokemonService(
        repository=repository,
        trainer_service=trainer_service,
        pokemon_service=pokemon_service,
        my_pokemon_move_service=my_pokemon_move_service,
    )
    service.list_all = AsyncMock(return_value=set())

    with pytest.raises(HTTPException) as error:
        await service.create_owned_for_trainer(
            trainer_id=trainer_id,
            pokemon_name="bulbasaur",
            nickname="Bulba",
        )

    assert error.value.status_code == 500
    assert error.value.detail == "Could not load created My Pokemon"
    assert repository.session.rolled_back is True

