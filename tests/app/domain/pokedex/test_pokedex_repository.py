from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi_pagination import LimitOffsetParams

from app.domain.pokedex import repository as repository_module
from app.domain.pokedex.repository import PokedexRepository
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

    def add_all(self, entities):
        self.added.extend(entities)

    async def flush(self):
        self.flushed = True


def build_base_pokemon(name="bulbasaur"):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        order=1,
        deleted_at=None,
        types=[],
    )


def build_repository(session=None):
    return PokedexRepository(session or FakeSession())


@pytest.mark.asyncio
async def test_list_catalog_pokemon_returns_all_non_deleted_catalog_entries():
    session = FakeSession()
    session.scalars_result = [build_base_pokemon()]
    repository = PokedexRepository(session)

    result = await repository.list_catalog_pokemon()

    assert [item.name for item in result] == ["bulbasaur"]


@pytest.mark.asyncio
async def test_list_owned_without_pagination_returns_all_items():
    session = FakeSession()
    session.scalars_result = [
        SimpleNamespace(pokemon=SimpleNamespace(name="bulbasaur"))
    ]
    repository = PokedexRepository(session)

    result = await repository.list_owned(uuid4(), FilterPage.build(nickname="leaf"))

    assert len(result) == 1
    assert result[0].pokemon.name == "bulbasaur"


@pytest.mark.asyncio
async def test_list_owned_with_pagination_uses_meta_total_when_total_is_missing(
    monkeypatch,
):
    session = FakeSession()
    repository = PokedexRepository(session)
    item = SimpleNamespace(pokemon=SimpleNamespace(name="bulbasaur"))
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

    result = await repository.list_owned(
        uuid4(),
        FilterPage.build(
            limit=1,
            offset=0,
            nickname="leaf",
            pokemon_name="bulbasaur",
            discovered=True,
        ),
    )

    assert [entry.pokemon.name for entry in result.items] == ["bulbasaur"]
    assert result.meta.total == 7


@pytest.mark.asyncio
async def test_find_owned_detail_returns_matching_entity():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(pokemon=SimpleNamespace(name="bulbasaur"))
    repository = PokedexRepository(session)

    result = await repository.find_owned_detail(uuid4(), "bulbasaur")

    assert result.pokemon.name == "bulbasaur"


@pytest.mark.asyncio
async def test_create_for_trainer_persists_one_entry_per_catalog_pokemon():
    session = FakeSession()
    repository = PokedexRepository(session)
    trainer_id = uuid4()
    timestamp = datetime.now(timezone.utc)
    bulbasaur = build_base_pokemon("bulbasaur")
    squirtle = build_base_pokemon("squirtle")

    result = await repository.create_for_trainer(
        trainer_id=trainer_id,
        pokemons=[bulbasaur, squirtle],
        discovered_pokemon_name="bulbasaur",
        discovered_at=timestamp,
        attributes_by_pokemon_id={
            bulbasaur.id: {
                "level": 1,
                "experience": 0,
                "hp": 50,
                "max_hp": 50,
                "attack": 49,
                "defense": 49,
                "special_attack": 65,
                "special_defense": 65,
                "speed": 45,
            },
            squirtle.id: {
                "level": 1,
                "experience": 0,
                "hp": 49,
                "max_hp": 49,
                "attack": 48,
                "defense": 65,
                "special_attack": 50,
                "special_defense": 64,
                "speed": 43,
            },
        },
    )

    assert len(result) == 2
    assert session.flushed is True
    assert len(session.added) == 2
    assert session.added[0].trainer_id == trainer_id
    assert session.added[0].discovered is True
    assert session.added[0].discovered_at == timestamp
    assert session.added[1].discovered is False
    assert session.added[1].discovered_at is None


@pytest.mark.asyncio
async def test_mark_discovered_sets_timestamp_only_when_missing():
    repository = build_repository()
    entity = SimpleNamespace(discovered=False, discovered_at=None)

    async def fake_update(current):
        return current

    repository.update = fake_update
    timestamp = datetime.now(timezone.utc)

    result = await repository.mark_discovered(entity, discovered_at=timestamp)

    assert result is entity
    assert entity.discovered is True
    assert entity.discovered_at == timestamp


@pytest.mark.asyncio
async def test_mark_discovered_preserves_existing_timestamp():
    repository = build_repository()
    timestamp = datetime.now(timezone.utc)
    entity = SimpleNamespace(discovered=False, discovered_at=timestamp)

    async def fake_update(current):
        return current

    repository.update = fake_update

    await repository.mark_discovered(
        entity,
        discovered_at=datetime.now(timezone.utc),
    )

    assert entity.discovered is True
    assert entity.discovered_at == timestamp
