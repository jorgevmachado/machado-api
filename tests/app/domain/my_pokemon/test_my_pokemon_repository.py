from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi_pagination import LimitOffsetParams

from app.domain.trainer.my_pokemon import repository as repository_module
from app.domain.trainer.my_pokemon import MyPokemonRepository
from app.shared.schemas import FilterPage


class FakeSession:
    def __init__(self):
        self.scalars_result = []
        self.scalar_result = None
        self.added = []
        self.flushed = False

    async def scalars(self, _query):
        return SimpleNamespace(all=lambda: self.scalars_result)

    async def scalar(self, _query):
        return self.scalar_result

    def add(self, entity):
        self.added.append(entity)

    async def flush(self):
        self.flushed = True


def build_repository():
    return MyPokemonRepository(FakeSession())


@pytest.mark.asyncio
async def test_list_all_without_pagination_returns_all_items():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(name="bulbasaur")]
    repository = MyPokemonRepository(session)

    result = await repository.list_all(FilterPage.build(trainer_id=uuid4()))

    assert [item.name for item in result] == ["bulbasaur"]


@pytest.mark.asyncio
async def test_find_by_returns_scoped_entity():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(name="bulbasaur")
    repository = MyPokemonRepository(session)

    result = await repository.find_by(trainer_id=uuid4(), name="bulbasaur")

    assert result.name == "bulbasaur"


@pytest.mark.asyncio
async def test_find_by_applies_id_and_pokemon_name_filters():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(name="bulbasaur")
    repository = MyPokemonRepository(session)

    result = await repository.find_by(
        trainer_id=uuid4(),
        id=uuid4(),
        pokemon_name='bulbasaur',
    )

    assert result.name == 'bulbasaur'


@pytest.mark.asyncio
async def test_find_base_pokemon_returns_base_catalog_entry():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(name="bulbasaur")
    repository = MyPokemonRepository(session)

    result = await repository.find_base_pokemon("bulbasaur")

    assert result.name == "bulbasaur"


@pytest.mark.asyncio
async def test_list_existing_owned_names_returns_set():
    session = FakeSession()
    session.scalars_result = ["bulbasaur", "ivysaur"]
    repository = MyPokemonRepository(session)

    result = await repository.list_existing_owned_names(uuid4())

    assert result == {"bulbasaur", "ivysaur"}


@pytest.mark.asyncio
async def test_create_owned_persists_entity():
    session = FakeSession()
    repository = MyPokemonRepository(session)

    entity = await repository.create_owned(
        trainer_id=uuid4(),
        pokemon_id=uuid4(),
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

    assert entity in session.added
    assert session.flushed is True


@pytest.mark.asyncio
async def test_attach_moves_persists_associations():
    session = FakeSession()
    repository = MyPokemonRepository(session)
    moves = [
        SimpleNamespace(id=uuid4(), pp=35),
        SimpleNamespace(id=uuid4(), pp=40),
    ]

    await repository.attach_moves(my_pokemon_id=uuid4(), moves=moves)

    assert len(session.added) == 2
    assert session.flushed is True


@pytest.mark.asyncio
async def test_list_all_with_pagination_returns_custom_page(monkeypatch):
    session = FakeSession()
    repository = MyPokemonRepository(session)
    item = SimpleNamespace(name="bulbasaur")
    params = LimitOffsetParams(limit=1, offset=0)

    monkeypatch.setattr(repository_module, "is_paginate", lambda _page_filter: True)
    monkeypatch.setattr(
        repository_module,
        "get_limit_offset_params",
        lambda _page_filter: params,
    )

    async def fake_paginate(_session, _query, params=None):
        assert _session is session
        assert params == LimitOffsetParams(limit=1, offset=0)
        return SimpleNamespace(items=[item], meta=SimpleNamespace(total=7))

    monkeypatch.setattr(repository_module, "paginate", fake_paginate)

    result = await repository.list_all(
        FilterPage.build(
            trainer_id=uuid4(),
            limit=1,
            offset=0,
            name="bulba",
            pokemon_name="bulbasaur",
        )
    )

    assert [owned.name for owned in result.items] == ["bulbasaur"]
    assert result.meta.total == 7


@pytest.mark.asyncio
async def test_soft_delete_owned_move_marks_deleted_at_and_updates_entity():
    repository = build_repository()
    owned_move = SimpleNamespace(updated_at="2026-05-13T00:00:00Z", deleted_at=None)

    async def fake_update(entity):
        return entity

    repository.update = fake_update

    result = await repository.soft_delete_owned_move(owned_move)

    assert result is owned_move
    assert owned_move.deleted_at == owned_move.updated_at
