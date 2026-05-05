from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi_pagination import LimitOffsetPage
from fastapi_pagination import LimitOffsetParams

from app.domain.pokemon import business as pokemon_business
from app.domain.pokemon.ability.service import PokemonAbilityService
from app.domain.pokemon.encounter.service import PokemonEncounterService
from app.domain.pokemon.growth_rate.service import PokemonGrowthRateService
from app.domain.pokemon.habitat.service import PokemonHabitatService
from pydantic import BaseModel
from sqlalchemy import column

from app.domain.pokemon.image.repository import PokemonImageRepository
from app.domain.pokemon.image.schema import PokemonImageSchema
from app.domain.pokemon.image.service import PokemonImageService
from app.domain.pokemon.image.business import (
    ensure_image,
    ensure_other_image,
    get_image_source,
    get_list_images,
)
from app.domain.pokemon.move.service import PokemonMoveService
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.schema import PokemonSchema
from app.domain.pokemon.service import PokemonService
from app.domain.pokemon.shape.service import PokemonShapeService
from app.domain.pokemon.type.business import (
    _extract_damage_relation,
    _extract_damage_relations,
    ensure_badges,
    ensure_colors,
    ensure_damage_relations,
)
from app.domain.pokemon.type.schema import PokemonTypeDamageSchema, PokemonTypeSchema
from app.domain.pokemon.type.service import PokemonTypeService
from app.infrastructure.external_api.schemas import NamedExternalResourceSchema
from app.models import PokemonStatusEnum
from app.shared.schemas import FilterPage
from app.shared.utils.string import get_text_language


def _repo(find_by=None):
    repo = SimpleNamespace()
    repo.session = SimpleNamespace()
    repo.find_by = AsyncMock(return_value=find_by)
    repo.save = AsyncMock(side_effect=lambda entity: entity)
    repo.update = AsyncMock(side_effect=lambda entity: entity)
    return repo


def _text_entries():
    return [
        {
            "language": {"name": "en"},
            "version_group": {"name": "gold-silver"},
            "effect": "Does a thing",
            "short_effect": "Thing",
            "flavor_text": "Flavor",
            "description": "Description",
        }
    ]


@pytest.mark.asyncio
async def test_fragment_from_session_factories():
    session = SimpleNamespace()
    client = SimpleNamespace()

    assert isinstance(PokemonAbilityService.from_session(session, client), PokemonAbilityService)
    assert isinstance(PokemonEncounterService.from_session(session, client), PokemonEncounterService)
    assert isinstance(PokemonGrowthRateService.from_session(session, client), PokemonGrowthRateService)
    assert isinstance(PokemonHabitatService.from_session(session, client), PokemonHabitatService)
    assert isinstance(PokemonImageService.from_session(session), PokemonImageService)
    assert isinstance(PokemonMoveService.from_session(session, client), PokemonMoveService)
    assert isinstance(PokemonShapeService.from_session(session, client), PokemonShapeService)
    assert isinstance(PokemonTypeService.from_session(session, client), PokemonTypeService)


@pytest.mark.asyncio
async def test_ability_service_get_or_create_existing_and_new():
    existing = SimpleNamespace(order=1)
    repo = _repo(find_by=existing)
    service = PokemonAbilityService(repo, client=SimpleNamespace())

    assert await service.get_or_create(order=1) is existing

    external = SimpleNamespace(
        name="overgrow",
        effect_entries=_text_entries(),
        flavor_text_entries=_text_entries(),
    )
    repo = _repo(find_by=None)
    client = SimpleNamespace(get_ability=AsyncMock(return_value=external))
    service = PokemonAbilityService(repo, client=client)

    created = await service.get_or_create(
        order=65, url="https://pokeapi.co/api/v2/ability/65/", slot=1, is_hidden=True
    )

    assert created.name == "overgrow"
    assert created.slot == 1
    assert created.is_hidden is True
    assert created.short_effect == "Thing"


@pytest.mark.asyncio
async def test_ability_service_sync_and_missing_external():
    repo = _repo(find_by=None)
    client = SimpleNamespace(get_ability=AsyncMock(return_value=None))
    service = PokemonAbilityService(repo, client=client)

    with pytest.raises(ValueError, match="External ability"):
        await service.get_or_create(order=1)

    service.get_or_create = AsyncMock(return_value="ability")
    result = await service.sync_from_resources(
        [{"ability": {"url": "https://pokeapi.co/api/v2/ability/65/"}, "slot": 2, "is_hidden": True}]
    )
    assert result == ["ability"]


@pytest.mark.asyncio
async def test_move_service_get_or_create_existing_new_and_missing_external():
    existing = SimpleNamespace(order=1)
    service = PokemonMoveService(_repo(find_by=existing), client=SimpleNamespace())
    assert await service.get_or_create(order=1) is existing

    external = SimpleNamespace(
        pp=35,
        type=SimpleNamespace(name="grass"),
        name="tackle",
        power=None,
        target=SimpleNamespace(name="selected-pokemon"),
        effect_entries=_text_entries(),
        priority=0,
        accuracy=None,
        flavor_text_entries=_text_entries(),
        damage_class=SimpleNamespace(name="physical"),
        effect_chance=None,
    )
    repo = _repo(find_by=None)
    service = PokemonMoveService(
        repo, client=SimpleNamespace(get_move=AsyncMock(return_value=external))
    )
    created = await service.get_or_create(
        order=33, url="https://pokeapi.co/api/v2/move/33/"
    )
    assert created.power == 0
    assert created.accuracy == 0
    assert created.short_effect == "Thing"

    service = PokemonMoveService(
        _repo(find_by=None), client=SimpleNamespace(get_move=AsyncMock(return_value=None))
    )
    with pytest.raises(ValueError, match="External move"):
        await service.get_or_create(order=404)


@pytest.mark.asyncio
async def test_move_service_sync_from_resources():
    service = PokemonMoveService(_repo(), client=SimpleNamespace())
    service.get_or_create = AsyncMock(return_value="move")

    result = await service.sync_from_resources(
        [{"move": {"url": "https://pokeapi.co/api/v2/move/33/"}}]
    )

    assert result == ["move"]
    service.get_or_create.assert_awaited_once_with(
        order=33, url="https://pokeapi.co/api/v2/move/33/"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("service_cls, model_name", [
    (PokemonHabitatService, "PokemonHabitat"),
    (PokemonShapeService, "PokemonShape"),
])
async def test_simple_resource_services(service_cls, model_name):
    existing = SimpleNamespace(order=1)
    service = service_cls(_repo(find_by=existing), client=SimpleNamespace())
    assert await service.get_or_create(order=1) is existing
    assert await service.sync_from_resource(None) is None

    repo = _repo(find_by=None)
    service = service_cls(repo, client=SimpleNamespace())
    created = await service.sync_from_resource(
        {"name": "cave", "url": "https://pokeapi.co/api/v2/resource/1/"}
    )
    assert created.name == "cave"

    with pytest.raises(ValueError, match="Name cannot be None"):
        await service.get_or_create(order=2, url="url")
    with pytest.raises(ValueError, match="URL cannot be None"):
        await service.get_or_create(order=2, name="name")


@pytest.mark.asyncio
async def test_growth_rate_service_paths():
    existing = SimpleNamespace(order=1)
    service = PokemonGrowthRateService(_repo(find_by=existing), client=SimpleNamespace())
    assert await service.get_or_create(order=1) is existing
    assert await service.sync_from_resource(None) is None

    external = SimpleNamespace(
        name="medium",
        formula="x",
        descriptions=[{"language": {"name": "en"}, "description": "Medium"}],
    )
    repo = _repo(find_by=None)
    service = PokemonGrowthRateService(
        repo, client=SimpleNamespace(get_growth_rate=AsyncMock(return_value=external))
    )
    created = await service.sync_from_resource(
        {"url": "https://pokeapi.co/api/v2/growth-rate/2/"}
    )
    assert created.description == "Medium"

    service = PokemonGrowthRateService(
        _repo(find_by=None),
        client=SimpleNamespace(get_growth_rate=AsyncMock(return_value=None)),
    )
    with pytest.raises(ValueError, match="External growth rate"):
        await service.get_or_create(order=404)


@pytest.mark.asyncio
async def test_encounter_service_success_and_validation_paths():
    pokemon_id = uuid4()
    existing = SimpleNamespace(order=1)
    service = PokemonEncounterService(_repo(find_by=existing), client=SimpleNamespace())
    assert await service.get_or_create(pokemon_id=pokemon_id, order=1) is existing

    service = PokemonEncounterService(_repo(find_by=None), client=SimpleNamespace())
    valid_entry = {
        "location_area": {
            "name": "forest",
            "url": "https://pokeapi.co/api/v2/location-area/1/",
        },
        "version_details": [
            {
                "max_chance": 30,
                "version": {"name": "red"},
                "encounter_details": [
                    {
                        "method": {"name": "walk"},
                        "condition_values": [{"name": "morning"}],
                        "chance": 10,
                        "min_level": 3,
                        "max_level": 5,
                    }
                ],
            }
        ],
    }
    result = await service.sync_from_payload(pokemon_id, [valid_entry])
    assert result[0].condition == "morning"

    invalid_cases = [
        ({}, "Entry cannot be None"),
        ({"entry": True}, "URL cannot be None"),
        ({"url": "url"}, "Name cannot be None"),
        ({"url": "url", "name": "name"}, "version_details"),
        ({"url": "url", "name": "name", "version_details": [{}]}, "version"),
            (
                {"url": "url", "name": "name", "version_details": [{"version": {"name": ""}}]},
                "version name",
            ),
        (
            {
                "url": "url",
                "name": "name",
                "version_details": [{"version": {"name": "red"}}],
            },
            "encounter_details",
        ),
        (
            {
                "url": "url",
                "name": "name",
                "version_details": [
                    {"version": {"name": "red"}, "encounter_details": [None]}
                ],
            },
            "required fields",
        ),
        (
            {
                "url": "url",
                "name": "name",
                "version_details": [
                    {"version": {"name": "red"}, "encounter_details": [{"method": None}]}
                ],
            },
            "method",
        ),
        (
            {
                "url": "url",
                "name": "name",
                "version_details": [
                        {
                            "version": {"name": "red"},
                            "encounter_details": [{"method": {"name": ""}}],
                        }
                    ],
                },
            "method name",
        ),
    ]
    for entry, message in invalid_cases:
        with pytest.raises(ValueError, match=message):
            await service.get_or_create(
                pokemon_id=pokemon_id, order=99, url=entry.get("url"), name=entry.get("name"), entry=entry if entry else None
            )


def test_type_business_branches():
    assert ensure_colors().name == "default"
    assert ensure_colors("fire").background_color == "#fd7d24"
    assert ensure_colors("unknown").name == "unknown"

    default_badges = ensure_badges(None)
    assert default_badges.badge_url.endswith("/1.png")
    assert ensure_badges({}).badge_url == default_badges.badge_url
    assert ensure_badges({"generation-i": {}}).badge_url == default_badges.badge_url
    badges = ensure_badges(
        {
            "generation-viii": {
                "brilliant-diamond-shining-pearl": {"name_icon": "name", "symbol_icon": "symbol"},
                "sword-shield": {"name_icon": "shield", "symbol_icon": "shield-symbol"},
                "legends-arceus": {"name_icon": "legend", "symbol_icon": "legend-symbol"},
            }
        }
    )
    assert badges.badge_url == "name"
    assert badges.badge_shield_icon_url == "shield-symbol"

    empty_relations = ensure_damage_relations(None)
    assert empty_relations.weaknesses == []
    relations = ensure_damage_relations(
        {
            "double_damage_from": [{"name": "fire", "url": "https://pokeapi.co/api/v2/type/10/"}],
            "half_damage_from": [None, {"name": None, "url": "url"}],
            "double_damage_to": [{"name": "grass", "url": "https://pokeapi.co/api/v2/type/12/"}],
            "half_damage_to": [],
        }
    )
    assert relations.weaknesses[0].name == "fire"
    assert relations.strengths[0].name == "grass"
    assert _extract_damage_relations(None) == []
    assert _extract_damage_relation(None) is None
    assert _extract_damage_relation({"name": "", "url": ""}) is None


@pytest.mark.asyncio
async def test_type_service_paths():
    existing = SimpleNamespace(order=1, status=PokemonStatusEnum.COMPLETE)
    service = PokemonTypeService(_repo(find_by=existing), client=SimpleNamespace())
    existing_resource = await service.get_or_create(order=1, name="fire")
    assert existing_resource.pokemon_type is existing

    with pytest.raises(ValueError, match="Name cannot be None"):
        await PokemonTypeService(_repo(find_by=None), client=SimpleNamespace()).get_or_create(order=2)

    external = SimpleNamespace(sprites=None, damage_relations=None)
    repo = _repo(find_by=None)
    service = PokemonTypeService(
        repo, client=SimpleNamespace(get_type=AsyncMock(return_value=external))
    )
    created = await service.get_or_create(
        order=10, name="fire", url="https://pokeapi.co/api/v2/type/10/"
    )
    assert created.pokemon_type.name == "fire"

    service = PokemonTypeService(
        _repo(find_by=None), client=SimpleNamespace(get_type=AsyncMock(return_value=None))
    )
    with pytest.raises(ValueError, match="Failed to retrieve external type"):
        await service.get_or_create(order=99, name="missing")

    service = PokemonTypeService(_repo(find_by=None), client=SimpleNamespace())
    service.get_or_create = AsyncMock(side_effect=[None, SimpleNamespace(pokemon_type="damage")])
    damages = await service.sync_from_damages(
        [
            NamedExternalResourceSchema(name="skip", url="https://pokeapi.co/api/v2/type/1/"),
            NamedExternalResourceSchema(name="ok", url="https://pokeapi.co/api/v2/type/2/"),
        ]
    )
    assert damages == ["damage"]

    pokemon_type = SimpleNamespace(status=PokemonStatusEnum.INCOMPLETE, weaknesses=[], strengths=[])
    service.sync_from_damages = AsyncMock(side_effect=[["weak"], ["strong"]])
    updated = await service.update_damages(
        pokemon_type,
        [NamedExternalResourceSchema(name="weak", url="https://pokeapi.co/api/v2/type/1/")],
        [NamedExternalResourceSchema(name="strong", url="https://pokeapi.co/api/v2/type/2/")],
    )
    assert updated.status == PokemonStatusEnum.COMPLETE

    unchanged = SimpleNamespace(status=PokemonStatusEnum.INCOMPLETE)
    service.sync_from_damages = AsyncMock(return_value=[])
    assert await service.update_damages(unchanged, [], []) is unchanged

    synced_resource = SimpleNamespace(
        pokemon_type=SimpleNamespace(name="fire"),
        pokemon_type_weaknesses=[],
        pokemon_type_strengths=[],
    )
    service = PokemonTypeService(_repo(), client=SimpleNamespace())
    service.get_or_create = AsyncMock(side_effect=[synced_resource, None])
    service.update_damages = AsyncMock(return_value="updated-fire")
    synced = await service.sync_from_resources(
        [
            {"type": {"name": "fire", "url": "https://pokeapi.co/api/v2/type/10/"}},
            {"type": {"name": "skip", "url": "https://pokeapi.co/api/v2/type/99/"}},
        ]
    )
    assert synced == ["updated-fire"]


@pytest.mark.asyncio
async def test_type_service_get_or_create_without_damage_relations(monkeypatch):
    monkeypatch.setattr(
        "app.domain.pokemon.type.service.ensure_damage_relations",
        lambda _relations: None,
    )
    repo = _repo(find_by=None)
    service = PokemonTypeService(
        repo,
        client=SimpleNamespace(
            get_type=AsyncMock(return_value=SimpleNamespace(sprites=None, damage_relations={}))
        ),
    )

    created = await service.get_or_create(order=10, name="fire")

    assert created.pokemon_type.name == "fire"
    assert created.pokemon_type_weaknesses == []
    assert created.pokemon_type_strengths == []


@pytest.mark.asyncio
async def test_type_service_find_one_enriches_incomplete_and_returns_complete(monkeypatch):
    incomplete = SimpleNamespace(name="fire", status=PokemonStatusEnum.INCOMPLETE)
    service = PokemonTypeService(_repo(find_by=incomplete), client=SimpleNamespace())
    service.cache_service.delete_domain = AsyncMock()
    service.client.get_type = AsyncMock(
        return_value=SimpleNamespace(
            damage_relations={
                "double_damage_from": [{"name": "water", "url": "https://pokeapi.co/api/v2/type/11/"}],
                "half_damage_from": [],
                "double_damage_to": [],
                "half_damage_to": [],
            }
        )
    )
    service.update_damages = AsyncMock(return_value="updated")

    assert await service.find_one("fire") == "updated"
    service.cache_service.delete_domain.assert_awaited_once()

    complete = SimpleNamespace(name="water", status=PokemonStatusEnum.COMPLETE)
    service = PokemonTypeService(_repo(find_by=complete), client=SimpleNamespace())
    assert await service.find_one("water") is complete

    incomplete = SimpleNamespace(name="missing", status=PokemonStatusEnum.INCOMPLETE)
    service = PokemonTypeService(_repo(find_by=incomplete), client=SimpleNamespace())
    service.client.get_type = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="Failed to retrieve external type"):
        await service.find_one("missing")

    incomplete = SimpleNamespace(name="plain", status=PokemonStatusEnum.INCOMPLETE)
    service = PokemonTypeService(_repo(find_by=incomplete), client=SimpleNamespace())
    service.client.get_type = AsyncMock(return_value=SimpleNamespace(damage_relations=None))
    monkeypatch.setattr(
        "app.domain.pokemon.type.service.ensure_damage_relations",
        lambda _relations: None,
    )
    assert await service.find_one("plain") is incomplete


def test_image_schema_serialization_branches():
    now = datetime.now(timezone.utc)
    schema = PokemonImageSchema(
        id=uuid4(),
        order=1,
        images='["a", "", "b"]',
        back_image="back",
        front_image="front",
        back_source="back_default",
        front_source="front_default",
        created_at=now,
    )
    assert schema.images == ["a", "b"]
    assert schema.serialize()["front_image"] == "front"
    assert PokemonImageSchema._serialize_images('{"a","b"}') == ["a", "b"]
    assert PokemonImageSchema._serialize_images("{}") == []
    assert PokemonImageSchema._serialize_images("[") == ["["]
    assert PokemonImageSchema._serialize_images("[bad]") == []
    assert PokemonImageSchema._serialize_images("single") == ["single"]
    assert PokemonImageSchema._serialize_images(None) == []
    assert PokemonImageSchema._serialize_images(["a", "", 1]) == ["a", "1"]


def test_image_business_remaining_branches():
    assert ensure_other_image("home", "front_default", None) is None
    assert ensure_other_image("home", "front_default", {"official": {}}) is None
    assert ensure_image("front_default", None) is None
    assert get_image_source("front", sprites=None).image == ""
    assert get_image_source("front", sprites={}).image == ""
    fallback = get_image_source(
        "front",
        sprites={"other": {"home": {"front_shiny": "shiny"}}},
        sources=["shiny"],
    )
    assert fallback.image == "shiny"
    assert get_list_images(None) == []


@pytest.mark.asyncio
async def test_image_repository_and_service_paths(monkeypatch):
    monkeypatch.setattr(
        "app.domain.pokemon.image.repository.PokemonImage.pokemon_id",
        column("pokemon_id"),
        raising=False,
    )
    session = SimpleNamespace(
        execute=AsyncMock(return_value=None),
        add=lambda _image: None,
        flush=AsyncMock(return_value=None),
    )
    repository = PokemonImageRepository(session)
    images = [SimpleNamespace(id=uuid4())]
    assert await repository.replace_for_pokemon(uuid4(), images) == images

    existing = SimpleNamespace(id=uuid4())
    service = PokemonImageService(_repo(find_by=existing))
    assert await service.sync_from_sprites(1, {"front_default": "front"}) is existing
    assert await PokemonImageService(_repo(find_by=None)).sync_from_sprites(1, None) is None

    service = PokemonImageService(_repo(find_by=None))
    created = await service.sync_from_sprites(
        1,
        {
            "front_default": "front",
            "back_default": "back",
            "other": {"home": {"front_default": "home-front"}},
        },
    )
    assert created.front_image == "front"
    assert created.back_image == "back"
    assert "home-front" in created.images


def test_pokemon_business_serializers_and_stats():
    assert pokemon_business.first_english_flavor_text(
        [{"language": {"name": "pt"}, "flavor_text": "Nao"}, {"language": {"name": "en"}, "flavor_text": "Seed\nPokemon"}]
    ) == "Seed Pokemon"
    assert pokemon_business.first_english_flavor_text(None) is None
    assert pokemon_business.stats_by_name(
        {"stats": [{"base_stat": 10, "stat": {"name": "special-attack"}}]}
    ) == {"special_attack": 10}
    assert pokemon_business.result_list_cache_serialize(object()) is None

    pokemon = _pokemon_schema_with_relations(include_relations=False)
    assert pokemon_business.result_list_cache_serialize([pokemon])["type"] == "list"
    page = LimitOffsetPage[PokemonSchema](items=[pokemon], limit=1, offset=0, total=1)
    assert pokemon_business.result_list_cache_serialize(page)["type"] == "paginate"
    custom_page = pokemon_business.CustomLimitOffsetPage[PokemonSchema].create(
        [pokemon], LimitOffsetParams(limit=1, offset=0), total=1
    )
    assert pokemon_business.result_list_cache_serialize(custom_page)["type"] == "custom-paginate"
    assert pokemon_business.result_cache_serialize(pokemon)["name"] == "bulbasaur"


def _pokemon_schema_with_relations(include_relations=True):
    now = datetime.now(timezone.utc)
    damage = PokemonTypeDamageSchema(id=uuid4(), name="water")
    type_schema = PokemonTypeSchema(
        id=uuid4(),
        url="url",
        name="fire",
        order=10,
        text_color="#fff",
        background_color="#000",
        weaknesses=[damage],
        strengths=[damage],
        created_at=now,
    )
    move = {
        "id": uuid4(),
        "pp": 1,
        "url": "url",
        "name": "move",
        "type": "normal",
        "power": 1,
        "order": 1,
        "target": "target",
        "effect": "effect",
        "accuracy": 100,
        "short_effect": "short",
        "damage_class": "physical",
        "created_at": now,
    }
    ability = {"id": uuid4(), "url": "url", "name": "ability", "order": 1, "created_at": now}
    encounter = {
        "id": uuid4(),
        "url": "url",
        "name": "encounter",
        "order": 1,
        "chance": 1,
        "method": "walk",
        "version": "red",
        "min_level": 1,
        "max_level": 2,
        "condition": "",
        "max_chance": 10,
        "created_at": now,
    }
    named_resource = {
        "id": uuid4(),
        "url": "url",
        "name": "resource",
        "order": 1,
        "created_at": now,
    }
    growth_rate = {**named_resource, "formula": "x", "description": "desc"}
    image = {
        "id": uuid4(),
        "order": 1,
        "images": ["front"],
        "back_image": "back",
        "front_image": "front",
        "back_source": "back_default",
        "front_source": "front_default",
        "created_at": now,
    }
    return PokemonSchema(
        id=uuid4(),
        hp=1,
        name="bulbasaur",
        order=1,
        types=[type_schema] if include_relations else [],
        moves=[move] if include_relations else [],
        images=image if include_relations else None,
        speed=1,
        height=1,
        weight=1,
        shape=named_resource if include_relations else None,
        status=PokemonStatusEnum.COMPLETE,
        attack=1,
        defense=1,
        is_baby=False,
        habitat=named_resource if include_relations else None,
        abilities=[ability] if include_relations else [],
        encounters=[encounter] if include_relations else [],
        growth_rate=growth_rate if include_relations else None,
        gender_rate=1,
        is_mythical=False,
        is_legendary=False,
        capture_rate=1,
        hatch_counter=1,
        base_happiness=1,
        external_image="image",
        special_attack=1,
        special_defense=1,
        base_experience=1,
        has_gender_differences=False,
        created_at=now,
    )


def test_pokemon_type_and_pokemon_schema_serializers():
    pokemon = _pokemon_schema_with_relations()
    serialized = pokemon.serialize()

    assert serialized["types"][0]["weaknesses"][0]["name"] == "water"
    assert serialized["moves"][0]["name"] == "move"
    assert serialized["abilities"][0]["name"] == "ability"
    assert serialized["encounters"][0]["name"] == "encounter"
    assert serialized["images"]["front_image"] == "front"
    assert serialized["growth_rate"]["formula"] == "x"
    assert serialized["habitat"]["name"] == "resource"
    assert serialized["shape"]["name"] == "resource"


@pytest.mark.asyncio
async def test_pokemon_repository_methods():
    repository = PokemonRepository(SimpleNamespace())
    query = object()
    assert repository._apply_filters(query, None) is query

    session = SimpleNamespace(scalar=AsyncMock(return_value=0))
    repository = PokemonRepository(session)
    assert await repository.has_any() is False

    pokemon = SimpleNamespace()
    session.scalar = AsyncMock(return_value=pokemon)
    assert await repository.get_by_order(1) is pokemon

    result = SimpleNamespace(all=lambda: ["a", "b"])
    session.scalars = AsyncMock(return_value=result)
    assert await repository.list_by_names(set()) == []
    assert await repository.list_by_names({"a", "b"}) == ["a", "b"]

    session.add = lambda _entity: None
    session.flush = AsyncMock()
    created = await repository.create_minimal(
        name="bulbasaur", order=1, external_image="image"
    )
    assert created.name == "bulbasaur"

    repository.find_by = AsyncMock(side_effect=["by-order", "by-id", "by-name"])
    assert await repository.find_detail("1") == "by-order"
    assert await repository.find_detail(str(uuid4())) == "by-id"
    assert await repository.find_detail("bulbasaur") == "by-name"


@pytest.mark.asyncio
async def test_pokemon_service_remaining_paths():
    repository = SimpleNamespace(
        session=SimpleNamespace(commit=AsyncMock()),
        has_any=AsyncMock(return_value=False),
        get_by_order=AsyncMock(side_effect=[object(), None]),
        create_minimal=AsyncMock(),
        list_all=AsyncMock(side_effect=RuntimeError("boom")),
        list_by_names=AsyncMock(return_value=[]),
        find_detail=AsyncMock(return_value=None),
    )
    client = SimpleNamespace(
        list_pokemon=AsyncMock(
            return_value=SimpleNamespace(
                results=[
                    SimpleNamespace(name="skip", url="https://pokeapi.co/api/v2/pokemon/1/"),
                    SimpleNamespace(name="create", url="https://pokeapi.co/api/v2/pokemon/2/"),
                ]
            )
        )
    )
    service = PokemonService(
        repository,
        client=client,
        type_service=SimpleNamespace(sync_from_resources=AsyncMock(return_value=[])),
        ability_service=SimpleNamespace(sync_from_resources=AsyncMock(return_value=[])),
        move_service=SimpleNamespace(sync_from_resources=AsyncMock(return_value=[])),
        image_service=SimpleNamespace(sync_from_sprites=AsyncMock(return_value=None)),
        growth_rate_service=SimpleNamespace(sync_from_resource=AsyncMock(return_value=None)),
        habitat_service=SimpleNamespace(sync_from_resource=AsyncMock(return_value=None)),
        shape_service=SimpleNamespace(sync_from_resource=AsyncMock(return_value=None)),
        encounter_service=SimpleNamespace(sync_from_payload=AsyncMock(return_value=[])),
    )
    await service._ensure_initial_catalog()
    repository.create_minimal.assert_awaited_once()

    with pytest.raises(HTTPException):
        await service.list_all()

    service.list_cache_service.get_list = AsyncMock(side_effect=RuntimeError("cache boom"))
    with pytest.raises(HTTPException):
        await service.list_all_cached()

    cached = object()
    service.cache_service.get_one = AsyncMock(return_value=cached)
    assert await service.find_detail("cached") is cached

    assert service._collect_evolution_names(None) == set()
    assert service._collect_evolution_names(
        {"species": {"name": "a"}, "evolves_to": [{"species": {"name": "b"}}]}
    ) == {"a", "b"}

    pokemon = SimpleNamespace(evolution_chain=None)
    assert await service._sync_evolution_chain(pokemon) == []

    pokemon = SimpleNamespace(id=uuid4(), evolution_chain="https://chain")
    other = SimpleNamespace(id=uuid4(), name="ivysaur")
    service.client.get_evolution_chain_by_url = AsyncMock(
        return_value=SimpleNamespace(
            model_dump=lambda: {
                "chain": {
                    "species": {"name": "bulbasaur"},
                    "evolves_to": [{"species": {"name": "ivysaur"}}],
                }
            }
        )
    )
    service.repository.list_by_names = AsyncMock(return_value=[pokemon, other])
    assert await service._sync_evolution_chain(pokemon) == [other]


def test_shared_schema_and_text_language_branches():
    page = FilterPage(page=1).with_updates(name="pikachu", limit=None)
    assert page.name == "pikachu"

    assert get_text_language([], "text").error is True
    assert get_text_language([{"language": {"name": "en"}}], "missing").error is True
    class EntryModel(BaseModel):
        language: dict
        version_group: dict
        flavor_text: str

    grouped = get_text_language(
        [
            EntryModel(language={"name": "pt"}, version_group={"name": "old"}, flavor_text="fallback"),
            {
                "language": {"name": "en"},
                "version_group": {"name": "ruby-sapphire"},
                "flavor_text": "grouped",
            },
        ],
        "flavor_text",
        group="ruby-sapphire",
    )
    assert grouped.text == "grouped"
    assert get_text_language([[("language", {"name": "en"}), ("text", "tuple")]], "text").text == "tuple"
