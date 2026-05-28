from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.encounter.service import EncounterService


class TestEncounterService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resources_collects_only_created_items(
        encounter_repository_mock: AsyncMock,
    ) -> None:
        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )
        service.get_or_create = AsyncMock(
            side_effect=[SimpleNamespace(name="route-1"), None]
        )

        result = await service.sync_from_resources([{"name": "route-1"}, {}])

        assert [item.name for item in result] == ["route-1"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_raises_without_entry(
        encounter_repository_mock: AsyncMock,
    ) -> None:
        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )

        with pytest.raises(ValueError, match="Entry cannot be None"):
            await service.get_or_create(None)

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_entity(
        encounter_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="route-1")
        encounter_repository_mock.find_by.return_value = existing
        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )

        result = await service.get_or_create(
            {
                "location_area": {
                    "name": "route-1",
                    "url": "https://pokeapi.co/api/v2/location-area/1/",
                },
                "version_details": [
                    {
                        "max_chance": 20,
                        "version": {"name": "red"},
                        "encounter_details": [
                            {
                                "method": {"name": "walk"},
                                "chance": 10,
                                "max_level": 5,
                                "min_level": 2,
                                "condition_values": [],
                            }
                        ],
                    }
                ],
            }
        )

        assert result is existing

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_raises_when_required_fields_missing(
        encounter_repository_mock: AsyncMock,
    ) -> None:
        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )

        with pytest.raises(ValueError, match="version_details"):
            await service.get_or_create(
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [],
                }
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_saves_new_encounter(
        encounter_repository_mock: AsyncMock,
    ) -> None:
        saved = SimpleNamespace(name="route-1")
        encounter_repository_mock.save.return_value = saved
        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )

        result = await service.get_or_create(
            {
                "location_area": {
                    "name": "route-1",
                    "url": "https://pokeapi.co/api/v2/location-area/1/",
                },
                "version_details": [
                    {
                        "max_chance": 20,
                        "version": {"name": "red"},
                        "encounter_details": [
                            {
                                "method": {"name": "walk"},
                                "chance": 10,
                                "max_level": 5,
                                "min_level": 2,
                                "condition_values": [{"name": "swarm"}],
                            }
                        ],
                    }
                ],
            }
        )

        assert result is saved
        saved_entity = encounter_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.method == "walk"
        assert saved_entity.condition == "swarm"

    @staticmethod
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("entry", "message"),
        [
            (
                {
                    "location_area": {
                        "name": None,
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [{}],
                },
                "Name and URL cannot be None",
            ),
            (
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [{"version": None, "encounter_details": [{}]}],
                },
                "version",
            ),
            (
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [
                        {"version": {"name": None}, "encounter_details": [{}]}
                    ],
                },
                "version name",
            ),
            (
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [
                        {"version": {"name": "red"}, "encounter_details": []}
                    ],
                },
                "encounter_details",
            ),
            (
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [
                        {"version": {"name": "red"}, "encounter_details": [None]}
                    ],
                },
                "required fields",
            ),
            (
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [
                        {
                            "version": {"name": "red"},
                            "encounter_details": [{"method": None}],
                        }
                    ],
                },
                "method",
            ),
            (
                {
                    "location_area": {
                        "name": "route-1",
                        "url": "https://pokeapi.co/api/v2/location-area/1/",
                    },
                    "version_details": [
                        {
                            "version": {"name": "red"},
                            "encounter_details": [{"method": {"name": None}}],
                        }
                    ],
                },
                "method name",
            ),
        ],
    )
    async def test_get_or_create_raises_for_invalid_nested_fields(
        encounter_repository_mock: AsyncMock,
        entry: dict,
        message: str,
    ) -> None:
        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )

        with pytest.raises(ValueError, match=message):
            await service.get_or_create(entry)

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_raises_when_location_area_resolves_to_falsy_resource(
        encounter_repository_mock: AsyncMock,
    ) -> None:
        class _ToggleBoolEntry(dict):
            def __init__(self) -> None:
                super().__init__({"location_area": None})
                self._bool_calls = 0

            def __bool__(self) -> bool:
                self._bool_calls += 1
                return self._bool_calls == 1

        service = EncounterService(
            repository=encounter_repository_mock, client=AsyncMock()
        )

        with pytest.raises(ValueError, match="Entry cannot be None"):
            await service.get_or_create(_ToggleBoolEntry())
