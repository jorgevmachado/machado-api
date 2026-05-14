from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi_pagination import LimitOffsetParams
from fastapi import HTTPException

from app.core.pagination import CustomLimitOffsetPage
from app.domain.my_pokemon.schema import CreateMyPokemonSchema
from app.domain.my_pokemon.service import MyPokemonService
from app.models.enums import RoleEnum
from app.shared.schemas import FilterPage


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


@pytest.mark.asyncio
async def test_create_requires_existing_trainer():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer_service = FakeTrainerService(trainer=None)
    service = MyPokemonService(repository, trainer_service)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
            CreateMyPokemonSchema(pokemon_name="bulbasaur"),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_persists_owned_pokemon_when_trainer_exists(monkeypatch):
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
        lambda _min, _max: 1.0,
    )
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer_service = FakeTrainerService(
        trainer=SimpleNamespace(
            id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75
        )
    )
    service = MyPokemonService(repository, trainer_service)
    service._invalidate_cache = AsyncMock()

    result = await service.create(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        CreateMyPokemonSchema(pokemon_name="bulbasaur", nickname="Leaf"),
    )

    assert repository.created_payload["nickname"] == "Leaf"
    assert result.nickname == "Leaf"


@pytest.mark.asyncio
async def test_create_uses_base_name_as_public_name_when_collision(monkeypatch):
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
        lambda _min, _max: 1.0,
    )
    repository = FakeRepository(
        base_pokemon=build_base_pokemon(),
        existing_names={"bulbasaur"},
    )
    trainer_service = FakeTrainerService(
        trainer=SimpleNamespace(
            id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75
        )
    )
    service = MyPokemonService(repository, trainer_service)
    service._invalidate_cache = AsyncMock()

    result = await service.create(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        CreateMyPokemonSchema(pokemon_name="bulbasaur", nickname="bulbasaur"),
    )

    assert repository.created_payload["name"] == "bulbasaur-2"
    assert result.name == "bulbasaur-2"


@pytest.mark.asyncio
async def test_list_all_cached_returns_cache_hit():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer_service = FakeTrainerService(
        trainer=SimpleNamespace(
            id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75
        )
    )
    service = MyPokemonService(repository, trainer_service)
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
async def test_find_detail_uses_cache_hit():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    trainer_service = FakeTrainerService(trainer=trainer)
    service = MyPokemonService(repository, trainer_service)
    cached = SimpleNamespace(name="bulbasaur")
    service.cache_service.get_one = AsyncMock(return_value=cached)
    service.cache_service.set_one = AsyncMock()
    service.repository.find_owned_detail = AsyncMock()

    result = await service.find_detail(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
    )

    assert result is cached
    service.repository.find_owned_detail.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_detail_raises_not_found_when_owned_pokemon_missing():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    trainer_service = FakeTrainerService(
        trainer=SimpleNamespace(
            id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75
        )
    )
    service = MyPokemonService(repository, trainer_service)
    service.cache_service.get_one = AsyncMock(return_value=None)
    service.cache_service.set_one = AsyncMock()
    service.repository.find_owned_detail = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.find_detail(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_list_and_detail_keys_when_name_is_provided():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    service = MyPokemonService(repository, FakeTrainerService())
    service.list_cache_service.delete_domain = AsyncMock()
    service.cache_service.cache.delete_cache = AsyncMock()

    await service._invalidate_cache("trainer-id", "bulbasaur")

    service.list_cache_service.delete_domain.assert_awaited_once()
    service.cache_service.cache.delete_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_all_cached_cleans_cache_and_stores_serialized_list():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    repository.created_entity = await repository.create_owned(
        trainer_id=uuid4(),
        pokemon_id=repository.base_pokemon.id,
        name="bulbasaur",
        nickname="bulbasaur",
        attributes={
            "level": 1,
            "experience": 0,
            "hp": 45,
            "max_hp": 45,
            "attack": 49,
            "defense": 49,
            "special_attack": 65,
            "special_defense": 65,
            "speed": 45,
        },
    )
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    trainer_service = FakeTrainerService(trainer=trainer)
    service = MyPokemonService(repository, trainer_service)
    service.list_cache_service.delete_domain = AsyncMock()
    service.list_cache_service.get_list = AsyncMock(return_value=None)
    service.list_cache_service.set_list = AsyncMock()

    page_filter = FilterPage.build(clean_cache=True)
    result = await service.list_all_cached(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER),
        page_filter,
    )

    assert result[0].name == "bulbasaur"
    assert page_filter.clean_cache is None
    service.list_cache_service.delete_domain.assert_awaited_once()
    service.list_cache_service.set_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_detail_serializes_and_caches_on_cache_miss():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    created_entity = await repository.create_owned(
        trainer_id=uuid4(),
        pokemon_id=repository.base_pokemon.id,
        name="bulbasaur",
        nickname="Leaf",
        attributes={
            "level": 1,
            "experience": 0,
            "hp": 45,
            "max_hp": 45,
            "attack": 49,
            "defense": 49,
            "special_attack": 65,
            "special_defense": 65,
            "speed": 45,
        },
    )
    trainer = SimpleNamespace(id=uuid4(), user_id=uuid4(), pokeballs=1, capture_rate=75)
    trainer_service = FakeTrainerService(trainer=trainer)
    service = MyPokemonService(repository, trainer_service)
    service.cache_service.get_one = AsyncMock(return_value=None)
    service.cache_service.set_one = AsyncMock()
    service.repository.find_owned_detail = AsyncMock(return_value=created_entity)

    result = await service.find_detail(
        SimpleNamespace(id=uuid4(), role=RoleEnum.USER), "bulbasaur"
    )

    assert result.nickname == "Leaf"
    service.cache_service.set_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trainer_or_404_raises_when_trainer_does_not_exist():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    service = MyPokemonService(repository, FakeTrainerService(trainer=None))

    with pytest.raises(HTTPException) as exc_info:
        await service._get_trainer_or_404(
            SimpleNamespace(id=uuid4(), role=RoleEnum.USER)
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_owned_for_trainer_rolls_back_when_base_pokemon_is_missing():
    repository = FakeRepository(base_pokemon=None)
    service = MyPokemonService(repository, FakeTrainerService())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_owned_for_trainer(
            trainer_id=uuid4(),
            pokemon_name="missingno",
            nickname=None,
        )

    assert exc_info.value.status_code == 404
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_create_owned_for_trainer_raises_internal_error_when_reload_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
        lambda _min, _max: 1.0,
    )
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    repository.find_owned_detail = AsyncMock(return_value=None)
    service = MyPokemonService(repository, FakeTrainerService())
    service._invalidate_cache = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await service.create_owned_for_trainer(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
        )

    assert exc_info.value.status_code == 500
    assert repository.session.rolled_back is True


@pytest.mark.asyncio
async def test_create_owned_for_trainer_does_not_rollback_when_commit_is_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
        lambda _min, _max: 1.0,
    )
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    repository.attach_moves = AsyncMock(side_effect=RuntimeError("boom"))
    service = MyPokemonService(repository, FakeTrainerService())

    with pytest.raises(RuntimeError, match="boom"):
        await service.create_owned_for_trainer(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            commit=False,
        )

    assert repository.session.rolled_back is False


def test_serialize_page_or_list_returns_serialized_custom_page():
    repository = FakeRepository(base_pokemon=build_base_pokemon())
    service = MyPokemonService(repository, FakeTrainerService())
    entity = SimpleNamespace(
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
        captured_at="2026-05-12T00:00:00Z",
        created_at="2026-05-12T00:00:00Z",
        updated_at=None,
        pokemon=repository.base_pokemon,
        trainer=SimpleNamespace(
            id=uuid4(),
            user_id=uuid4(),
            pokeballs=1,
            capture_rate=75,
        ),
        moves=[],
    )
    page = CustomLimitOffsetPage.create(
        items=[entity],
        params=LimitOffsetParams(limit=10, offset=0),
        total=1,
    )

    result = service._serialize_page_or_list(page)

    assert isinstance(result, CustomLimitOffsetPage)
    assert result.items[0].name == "bulbasaur"
