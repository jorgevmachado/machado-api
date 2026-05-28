from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.pokemon.service import PokemonService
from app.models import Pokemon, PokemonStatusEnum


class TestPokemonService:
    @staticmethod
    def test_from_session_builds_service() -> None:
        service = PokemonService.from_session(AsyncMock())

        assert isinstance(service, PokemonService)

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_returns_repository_page(
        pokemon_service: PokemonService,
        pokemon_page: SimpleNamespace,
    ) -> None:
        result = await pokemon_service.list_all()

        assert result is pokemon_page

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_cached_sets_cache_on_miss(
        pokemon_service: PokemonService,
        pokemon_page: SimpleNamespace,
    ) -> None:
        pokemon_service.list_all = AsyncMock(return_value=pokemon_page)
        pokemon_service.cache_service = SimpleNamespace(
            get_list=AsyncMock(return_value=None),
            set_list=AsyncMock(),
            build_key_list=lambda *_args, **_kwargs: "pokemon:list:key",
        )

        result = await pokemon_service.list_all_cached()

        assert result is pokemon_page
        assert pokemon_service.cache_service.set_list.await_args.args[:2] == (
            "pokemon:list:key",
            pokemon_page,
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_cached_cleans_cache_and_returns_hit(
        pokemon_service: PokemonService,
    ) -> None:
        cached = SimpleNamespace(items=["cached"])
        page_filter = SimpleNamespace(clean_cache=True)
        pokemon_service.cache_service = SimpleNamespace(
            build_key_one=lambda **_kwargs: "pokemon:one:meta",
            build_key_list=lambda **_kwargs: "pokemon:list:key",
            delete_cache=AsyncMock(),
            get_list=AsyncMock(return_value=cached),
            set_list=AsyncMock(),
        )

        result = await pokemon_service.list_all_cached(page_filter=page_filter)

        assert result is cached
        assert page_filter.clean_cache is None
        pokemon_service.cache_service.delete_cache.assert_awaited_once()
        pokemon_service.cache_service.set_list.assert_not_awaited()

    @staticmethod
    @pytest.mark.asyncio
    async def test_ensure_initial_catalog_returns_when_meta_is_cached(
        pokemon_repository_mock: SimpleNamespace,
        pokemon_service_factory,
    ) -> None:
        pokemon_service = pokemon_service_factory(pokemon_repository_mock)
        pokemon_service.cache_service.get_cache = AsyncMock(return_value={"ok": True})
        pokemon_service.repository.total = AsyncMock()

        await pokemon_service._ensure_initial_catalog()

        pokemon_service.repository.total.assert_not_awaited()

    @staticmethod
    @pytest.mark.asyncio
    async def test_ensure_initial_catalog_populates_missing_entries(
        pokemon_repository_mock: SimpleNamespace,
        pokemon_service_factory,
    ) -> None:
        pokemon_service = pokemon_service_factory(pokemon_repository_mock)
        pokemon_service.cache_service.get_cache = AsyncMock(return_value=None)
        pokemon_service.cache_service.set_cache = AsyncMock()
        pokemon_service.repository.total = AsyncMock(return_value=0)
        pokemon_service.repository.find_by = AsyncMock(
            side_effect=[None, SimpleNamespace()]
        )
        pokemon_service.repository.save = AsyncMock()
        pokemon_service.client.total_pokemon = AsyncMock(return_value=2)
        pokemon_service.client.list_pokemon = AsyncMock(
            return_value=SimpleNamespace(
                count=2,
                results=[
                    SimpleNamespace(
                        name="bulbasaur", url="https://pokeapi.co/api/v2/pokemon/1/"
                    ),
                    SimpleNamespace(
                        name="ivysaur", url="https://pokeapi.co/api/v2/pokemon/2/"
                    ),
                ],
            )
        )

        await pokemon_service._ensure_initial_catalog()

        pokemon_service.repository.save.assert_awaited_once()
        pokemon_service.cache_service.set_cache.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_raises_not_found_when_repository_returns_none(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon_service.repository.find_by = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exception:
            await pokemon_service.find_one("missing")

        assert exception.value.status_code == 404

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_returns_enriched_pokemon(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon = Pokemon(name="bulbasaur", order=1, external_image="image")
        pokemon_service.repository.find_by = AsyncMock(return_value=pokemon)
        pokemon_service._enrich_if_needed = AsyncMock(return_value=pokemon)

        result = await pokemon_service.find_one("bulbasaur", user_request="username")

        assert result is pokemon

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_cached_refreshes_incomplete_cached_payload(
        pokemon_service: PokemonService,
    ) -> None:
        cached = SimpleNamespace(
            model_dump=lambda: {"status": PokemonStatusEnum.INCOMPLETE},
        )
        enriched = Pokemon(name="bulbasaur", order=1, external_image="image")
        pokemon_service.cache_service.get_one = AsyncMock(return_value=cached)
        pokemon_service.cache_service.set_one = AsyncMock()
        pokemon_service._enrich_if_needed = AsyncMock(return_value=enriched)

        result = await pokemon_service.find_one_cached("bulbasaur")

        assert result is enriched
        pokemon_service.cache_service.set_one.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_cached_deletes_and_sets_on_cache_miss(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon = Pokemon(name="bulbasaur", order=1, external_image="image")
        pokemon_service.cache_service.get_one = AsyncMock(return_value=None)
        pokemon_service.cache_service.delete_cache = AsyncMock()
        pokemon_service.cache_service.set_one = AsyncMock()
        pokemon_service.find_one = AsyncMock(return_value=pokemon)

        result = await pokemon_service.find_one_cached("bulbasaur", clean_cache=True)

        assert result is pokemon
        pokemon_service.cache_service.delete_cache.assert_awaited_once()
        pokemon_service.cache_service.set_one.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_enrich_if_needed_returns_complete_pokemon_without_changes(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon = Pokemon(name="bulbasaur", order=1, external_image="image")
        pokemon.status = PokemonStatusEnum.COMPLETE

        result = await pokemon_service._enrich_if_needed(pokemon)

        assert result is pokemon

    @staticmethod
    @pytest.mark.asyncio
    async def test_enrich_if_needed_populates_and_updates_incomplete_pokemon(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon = Pokemon(name="bulbasaur", order=1, external_image="image")
        pokemon.status = PokemonStatusEnum.INCOMPLETE
        pokemon.id = uuid4()
        pokemon.evolution_chain = "https://pokeapi.co/api/v2/evolution-chain/1/"

        pokemon_service.client.get_pokemon = AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda: {
                    "height": 7,
                    "weight": 69,
                    "base_experience": 64,
                    "stats": [
                        {"base_stat": 45, "stat": {"name": "hp"}},
                        {"base_stat": 49, "stat": {"name": "attack"}},
                        {"base_stat": 49, "stat": {"name": "defense"}},
                        {"base_stat": 65, "stat": {"name": "special-attack"}},
                        {"base_stat": 65, "stat": {"name": "special-defense"}},
                        {"base_stat": 45, "stat": {"name": "speed"}},
                    ],
                    "types": [
                        {
                            "type": {
                                "name": "grass",
                                "url": "https://pokeapi.co/api/v2/type/12/",
                            }
                        }
                    ],
                    "moves": [
                        {
                            "move": {
                                "name": "tackle",
                                "url": "https://pokeapi.co/api/v2/move/33/",
                            }
                        }
                    ],
                    "abilities": [
                        {
                            "ability": {
                                "name": "overgrow",
                                "url": "https://pokeapi.co/api/v2/ability/65/",
                            }
                        }
                    ],
                    "sprites": {
                        "front_default": "front-url",
                        "back_default": "back-url",
                    },
                }
            )
        )
        pokemon_service.client.get_pokemon_species = AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda: {
                    "flavor_text_entries": [
                        {
                            "language": {"name": "en"},
                            "flavor_text": "Seed Pokemon",
                        }
                    ],
                    "capture_rate": 45,
                    "is_baby": False,
                    "is_mythical": False,
                    "is_legendary": False,
                    "gender_rate": 1,
                    "hatch_counter": 20,
                    "base_happiness": 70,
                    "has_gender_differences": False,
                    "evolves_from_species": {"name": "none"},
                    "evolution_chain": {
                        "url": "https://pokeapi.co/api/v2/evolution-chain/1/"
                    },
                    "shape": {
                        "name": "quadruped",
                        "url": "https://pokeapi.co/api/v2/pokemon-shape/8/",
                    },
                    "habitat": {
                        "name": "forest",
                        "url": "https://pokeapi.co/api/v2/pokemon-habitat/2/",
                    },
                    "growth_rate": {
                        "name": "medium",
                        "url": "https://pokeapi.co/api/v2/growth-rate/2/",
                    },
                }
            )
        )
        pokemon_service.client.get_pokemon_encounters = AsyncMock(return_value=[])
        pokemon_service.type_service.sync_from_resources = AsyncMock(
            return_value=[SimpleNamespace(name="grass")]
        )
        pokemon_service.shape_service.sync_from_resource = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        pokemon_service.image_service.sync_from_sprites = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        pokemon_service.habitat_service.sync_from_resource = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        pokemon_service.growth_rate_service.sync_from_resource = AsyncMock(
            return_value=SimpleNamespace(id=uuid4())
        )
        pokemon_service.move_service.sync_from_resources = AsyncMock(
            return_value=[SimpleNamespace(name="tackle")]
        )
        pokemon_service.ability_service.sync_from_resources = AsyncMock(
            return_value=[SimpleNamespace(name="overgrow")]
        )
        pokemon_service.encounter_service.sync_from_resources = AsyncMock(
            return_value=[]
        )
        pokemon_service._sync_evolution_chain = AsyncMock(return_value=[])
        pokemon_service.repository.update = AsyncMock(return_value=pokemon)
        pokemon_service.repository.find_by = AsyncMock(return_value=None)

        result = await pokemon_service._enrich_if_needed(pokemon)

        assert result is pokemon
        assert pokemon.status == PokemonStatusEnum.COMPLETE
        pokemon_service.repository.update.assert_awaited_once_with(pokemon)

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_evolution_chain_handles_empty_chain(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon = Pokemon(name="bulbasaur", order=1, external_image="image")
        pokemon.evolution_chain = None

        result = await pokemon_service._sync_evolution_chain(pokemon)

        assert result == []

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_evolution_chain_excludes_current_pokemon(
        pokemon_service: PokemonService,
    ) -> None:
        pokemon = Pokemon(name="ivysaur", order=2, external_image="image")
        pokemon.id = uuid4()
        pokemon.evolution_chain = "https://pokeapi.co/api/v2/evolution-chain/1/"
        evolution = Pokemon(name="venusaur", order=3, external_image="image")
        evolution.id = uuid4()
        pokemon_service.client.get_evolution_chain_by_url = AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda: {
                    "chain": {
                        "species": {"name": "bulbasaur"},
                        "evolves_to": [
                            {
                                "species": {"name": "ivysaur"},
                                "evolves_to": [
                                    {"species": {"name": "venusaur"}, "evolves_to": []}
                                ],
                            }
                        ],
                    }
                }
            )
        )
        pokemon_service.repository.list_by_names = AsyncMock(
            return_value=[pokemon, evolution]
        )

        result = await pokemon_service._sync_evolution_chain(pokemon)

        assert result == [evolution]
