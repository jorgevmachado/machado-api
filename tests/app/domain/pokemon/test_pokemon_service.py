from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.pokemon.service import PokemonService
from app.models.enums import PokemonStatusEnum
from app.shared.schemas import FilterPage


class FakeRepository:
    session = SimpleNamespace(commit=lambda: None)

    def __init__(self):
        self.created = []

    async def has_any(self):
        return False

    async def get_by_order(self, _order):
        return None

    async def create_minimal(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeClient:
    def __init__(self):
        self.detail_called = False

    async def list_pokemon(self, offset=0, limit=1350):
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    name="bulbasaur", url="https://pokeapi.co/api/v2/pokemon/1/"
                ),
            ]
        )

    async def get_pokemon(self, *_args):
        self.detail_called = True


@pytest.mark.asyncio
async def test_initial_catalog_sync_uses_only_list_endpoint(monkeypatch):
    repository = FakeRepository()
    client = FakeClient()
    service = PokemonService(repository, client=client)

    async def commit():
        return None

    repository.session.commit = commit

    await service._ensure_initial_catalog()

    assert repository.created == [
        {
            "name": "bulbasaur",
            "order": 1,
            "external_image": "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/detail/001.png",
        }
    ]
    assert client.detail_called is False


def build_pokemon(status=PokemonStatusEnum.COMPLETE):
    return SimpleNamespace(
        id=uuid4(),
        order=1,
        name="bulbasaur",
        external_image="https://example.com/0001.png",
        status=status,
        types=[],
        moves=[],
        abilities=[],
        images=None,
        images_id=None,
        encounters=[],
        evolutions_from=[],
        evolutions=[],
        growth_rate=None,
        growth_rate_id=None,
        habitat=None,
        habitat_id=None,
        shape=None,
        shape_id=None,
        height=None,
        weight=None,
        base_experience=None,
        hp=None,
        attack=None,
        defense=None,
        special_attack=None,
        special_defense=None,
        speed=None,
        description=None,
        capture_rate=None,
        is_baby=None,
        is_mythical=None,
        is_legendary=None,
        gender_rate=None,
        hatch_counter=None,
        base_happiness=None,
        evolution_chain=None,
        evolves_from_species=None,
        has_gender_differences=None,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )


def build_service(repository, client=None):
    empty_collection_service = SimpleNamespace(
        sync_from_resources=AsyncMock(return_value=[])
    )
    return PokemonService(
        repository,
        client=client or AsyncMock(),
        type_service=empty_collection_service,
        ability_service=SimpleNamespace(sync_from_resources=AsyncMock(return_value=[])),
        move_service=empty_collection_service,
        image_service=SimpleNamespace(sync_from_sprites=AsyncMock()),
        growth_rate_service=SimpleNamespace(
            sync_from_resource=AsyncMock(return_value=None)
        ),
        habitat_service=SimpleNamespace(
            sync_from_resource=AsyncMock(return_value=None)
        ),
        shape_service=SimpleNamespace(sync_from_resource=AsyncMock(return_value=None)),
        encounter_service=SimpleNamespace(sync_from_payload=AsyncMock()),
    )


@pytest.mark.asyncio
async def test_list_all_returns_cache_hit_without_repository_query():
    repository = SimpleNamespace(
        session=SimpleNamespace(),
        has_any=AsyncMock(return_value=True),
        list_all=AsyncMock(),
    )
    service = build_service(repository)
    cached = SimpleNamespace(items=[])
    page_filter = FilterPage(clean_cache=True)
    service.cache_service.delete_domain = AsyncMock()
    service.list_cache_service = SimpleNamespace(
        get_list=AsyncMock(return_value=cached),
        set_list=AsyncMock(),
        cache=SimpleNamespace(build_key=lambda *_args: "pokemon:list:key"),
    )

    result = await service.list_all_cached(page_filter=page_filter)

    assert result is cached
    assert page_filter.clean_cache is None
    repository.list_all.assert_not_awaited()
    service.cache_service.delete_domain.assert_awaited_once()
    service.list_cache_service.set_list.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_all_sets_cache_on_miss():
    page = SimpleNamespace(items=[])
    repository = SimpleNamespace(
        session=SimpleNamespace(),
        has_any=AsyncMock(return_value=True),
        list_all=AsyncMock(return_value=page),
    )
    service = build_service(repository)
    service.list_cache_service = SimpleNamespace(
        get_list=AsyncMock(return_value=None),
        set_list=AsyncMock(),
        cache=SimpleNamespace(build_key=lambda *_args: "pokemon:list:key"),
    )

    result = await service.list_all_cached()

    assert result is page
    repository.list_all.assert_awaited_once()
    assert service.list_cache_service.set_list.await_args.args[:2] == (
        "pokemon:list:key",
        page,
    )


@pytest.mark.asyncio
async def test_invalidate_cache_removes_list_and_detail_entries():
    repository = SimpleNamespace(session=SimpleNamespace())
    service = build_service(repository)
    service.list_cache_service = SimpleNamespace(
        cache=SimpleNamespace(delete_pattern=AsyncMock()),
    )
    service.cache_service = SimpleNamespace(
        cache=SimpleNamespace(
            build_key=lambda *_args: "pokemon:detail:pikachu",
            delete_cache=AsyncMock(),
        ),
    )

    await service._invalidate_cache("pikachu")

    service.list_cache_service.cache.delete_pattern.assert_awaited_once_with(
        "pokemon:list*"
    )
    service.cache_service.cache.delete_cache.assert_awaited_once_with(
        "pokemon:detail:pikachu"
    )


@pytest.mark.asyncio
async def test_find_detail_raises_not_found_when_repository_returns_none():
    repository = SimpleNamespace(
        session=SimpleNamespace(),
        has_any=AsyncMock(return_value=True),
        find_detail=AsyncMock(return_value=None),
    )
    service = build_service(repository)
    service.cache_service = SimpleNamespace(
        get_one=AsyncMock(return_value=None),
        set_one=AsyncMock(),
        cache=SimpleNamespace(build_key=lambda *_args: "pokemon:detail:missing"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.find_detail("missing")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_find_detail_complete_pokemon_does_not_call_external_detail_api():
    pokemon = build_pokemon(PokemonStatusEnum.COMPLETE)
    client = AsyncMock()
    repository = SimpleNamespace(
        session=SimpleNamespace(),
        has_any=AsyncMock(return_value=True),
        find_detail=AsyncMock(return_value=pokemon),
        list_type_damage_relations=AsyncMock(return_value=[]),
    )
    service = build_service(repository, client)
    service.cache_service = SimpleNamespace(
        get_one=AsyncMock(return_value=None),
        set_one=AsyncMock(),
        cache=SimpleNamespace(
            build_key=lambda *_args: "pokemon:detail:bulbasaur",
            delete_cache=AsyncMock(),
        ),
    )

    result = await service.find_detail("bulbasaur")

    assert result.name == "bulbasaur"
    client.get_pokemon.assert_not_awaited()
    service.cache_service.set_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_detail_enriches_incomplete_pokemon_before_returning_detail():
    pokemon = build_pokemon(PokemonStatusEnum.INCOMPLETE)
    client = AsyncMock()
    client.get_pokemon.return_value = SimpleNamespace(
        model_dump=lambda: {
            "height": 7,
            "weight": 69,
            "base_experience": 64,
            "stats": [{"base_stat": 45, "stat": {"name": "hp"}}],
            "types": [],
            "moves": [],
            "abilities": [],
            "sprites": {},
        }
    )
    client.get_pokemon_species.return_value = SimpleNamespace(
        model_dump=lambda: {
            "flavor_text_entries": [
                {"language": {"name": "en"}, "flavor_text": "Seed Pokemon"}
            ],
            "capture_rate": 45,
        }
    )
    client.get_pokemon_encounters.return_value = []
    repository = SimpleNamespace(
        session=SimpleNamespace(commit=AsyncMock()),
        has_any=AsyncMock(return_value=True),
        find_detail=AsyncMock(side_effect=[pokemon, pokemon]),
        list_type_damage_relations=AsyncMock(return_value=[]),
    )
    service = build_service(repository, client)
    service.cache_service = SimpleNamespace(
        get_one=AsyncMock(return_value=None),
        set_one=AsyncMock(),
        cache=SimpleNamespace(
            build_key=lambda *_args: "pokemon:detail:bulbasaur",
            delete_cache=AsyncMock(),
        ),
    )
    service.list_cache_service = SimpleNamespace(
        cache=SimpleNamespace(delete_pattern=AsyncMock()),
    )

    result = await service.find_detail("bulbasaur")

    assert result.status == PokemonStatusEnum.COMPLETE
    assert result.height == 7
    assert pokemon.description == "Seed Pokemon"
    client.get_pokemon.assert_awaited_once_with("bulbasaur")
    client.get_pokemon_species.assert_awaited_once_with("bulbasaur")
    client.get_pokemon_encounters.assert_awaited_once_with(1)
