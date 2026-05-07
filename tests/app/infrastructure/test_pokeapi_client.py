from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.external_api.pokeapi_client import PokeApiClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    requested_urls: list[str] = []

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, url: str):
        self.requested_urls.append(url)
        if "pokemon?" in url:
            return FakeResponse(
                {
                    "count": 1,
                    "results": [
                        {
                            "name": "bulbasaur",
                            "url": "https://pokeapi.co/api/v2/pokemon/1/",
                        }
                    ],
                }
            )
        return FakeResponse({"id": 1, "name": "bulbasaur", "sprites": {}})


@pytest.mark.asyncio
async def test_list_pokemon_builds_expected_url(monkeypatch):
    FakeAsyncClient.requested_urls = []
    monkeypatch.setattr(
        "app.infrastructure.external_api.pokeapi_client.httpx.AsyncClient",
        FakeAsyncClient,
    )
    monkeypatch.setattr(
        "app.infrastructure.external_api.pokeapi_client.Settings",
        lambda: SimpleNamespace(
            POKEAPI_BASE_URL="https://pokeapi.co/api/v2",
            POKEAPI_CA_BUNDLE=None,
            POKEAPI_VERIFY_SSL=False,
        ),
    )
    client = PokeApiClient()

    result = await client.list_pokemon(offset=0, limit=1350)

    assert result.results[0].name == "bulbasaur"
    assert FakeAsyncClient.requested_urls == [
        "https://pokeapi.co/api/v2/pokemon?offset=0&limit=1350"
    ]


@pytest.mark.asyncio
async def test_get_pokemon_returns_typed_payload(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.external_api.pokeapi_client.httpx.AsyncClient",
        FakeAsyncClient,
    )
    monkeypatch.setattr(
        "app.infrastructure.external_api.pokeapi_client.Settings",
        lambda: SimpleNamespace(
            POKEAPI_BASE_URL="https://pokeapi.co/api/v2",
            POKEAPI_CA_BUNDLE=None,
            POKEAPI_VERIFY_SSL=False,
        ),
    )
    client = PokeApiClient()

    result = await client.get_pokemon("bulbasaur")

    assert result.id == 1
    assert result.name == "bulbasaur"


@pytest.mark.asyncio
async def test_pokeapi_client_remaining_methods(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.external_api.pokeapi_client.Settings",
        lambda: SimpleNamespace(
            POKEAPI_BASE_URL="https://pokeapi.co/api/v2/",
            POKEAPI_CA_BUNDLE="/tmp/ca.pem",
            POKEAPI_VERIFY_SSL=False,
        ),
    )
    client = PokeApiClient()

    async def fake_get(path_or_url):
        if path_or_url == "not-a-dict":
            return []
        if str(path_or_url).startswith("pokemon-species"):
            return {"id": 1, "name": "bulbasaur"}
        if str(path_or_url).endswith("/encounters"):
            return [{"location_area": {"name": "forest"}}]
        if str(path_or_url).startswith("move"):
            return {
                "id": 1,
                "pp": 35,
                "name": "tackle",
                "type": {"name": "normal", "url": "url"},
                "target": {"name": "selected-pokemon", "url": "url"},
                "priority": 0,
                "damage_class": {"name": "physical", "url": "url"},
            }
        if str(path_or_url).startswith("type"):
            return {"id": 1, "name": "normal"}
        if str(path_or_url).startswith("ability"):
            return {"id": 1, "name": "overgrow"}
        if str(path_or_url).startswith("growth-rate"):
            return {"id": 1, "name": "medium"}
        if str(path_or_url).startswith("http"):
            return {"id": 1, "name": "physical"}
        return {"id": 1, "name": "resource"}

    client._get = fake_get

    assert client.verify == "/tmp/ca.pem"
    assert (await client.get_resource_url("not-a-dict")).model_dump() == {}
    assert (await client.get_resource_url("resource")).id == 1
    assert (await client.get_pokemon_species("bulbasaur")).name == "bulbasaur"
    assert await client.get_pokemon_encounters(1) == [
        {"location_area": {"name": "forest"}}
    ]
    assert (await client.get_move(1)).name == "tackle"
    assert (await client.get_type(1)).name == "normal"
    assert (await client.get_ability(1)).name == "overgrow"
    assert (await client.get_growth_rate(1)).name == "medium"
    assert (
               await client.get_evolution_chain_by_url(
                   "https://pokeapi.co/api/v2/evolution-chain/1"
               )
           ).id == 1
    assert (
               await client.get_move_damage_class_by_url(
                   "https://pokeapi.co/api/v2/move-damage-class/1"
               )
           ).id == 1


@pytest.mark.asyncio
async def test_pokeapi_client_encounters_returns_empty_for_non_list(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.external_api.pokeapi_client.Settings",
        lambda: SimpleNamespace(
            POKEAPI_BASE_URL="https://pokeapi.co/api/v2",
            POKEAPI_CA_BUNDLE=None,
            POKEAPI_VERIFY_SSL=False,
        ),
    )
    client = PokeApiClient(
        base_url="https://pokeapi.co/api/v2/", verify=True, timeout=1
    )
    client._get = AsyncMock(return_value={"not": "list"})

    assert await client.get_pokemon_encounters(1) == []
