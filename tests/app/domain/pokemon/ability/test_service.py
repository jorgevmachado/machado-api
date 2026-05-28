from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.ability.service import AbilityService


class TestAbilityService:
    @pytest.mark.asyncio
    async def test_sync_from_resources_skips_none_results(
        self,
        ability_repository_mock: AsyncMock,
    ) -> None:
        service = AbilityService(repository=ability_repository_mock, client=AsyncMock())
        service.get_or_create = AsyncMock(
            side_effect=[SimpleNamespace(name="overgrow"), None]
        )

        result = await service.sync_from_resources(
            resources=[
                {"ability": {"url": "https://pokeapi.co/api/v2/ability/65/"}},
                {},
            ]
        )

        assert len(result) == 1
        assert result[0].name == "overgrow"

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_entity(
        self,
        ability_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="overgrow")
        ability_repository_mock.find_by.return_value = existing
        service = AbilityService(repository=ability_repository_mock, client=AsyncMock())

        result = await service.get_or_create(
            resource={"url": "https://pokeapi.co/api/v2/ability/65/"}
        )

        assert result is existing

    @pytest.mark.asyncio
    async def test_get_or_create_raises_when_external_resource_is_missing(
        self,
        ability_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_ability.return_value = None
        service = AbilityService(repository=ability_repository_mock, client=client)

        with pytest.raises(ValueError, match="External ability not found"):
            await service.get_or_create(
                resource={"url": "https://pokeapi.co/api/v2/ability/65/"}
            )

    @pytest.mark.asyncio
    async def test_get_or_create_saves_external_ability(
        self,
        ability_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_ability.return_value = SimpleNamespace(
            name="overgrow",
            effect_entries=[
                {
                    "language": {"name": "en"},
                    "effect": "Boosts grass moves.",
                    "short_effect": "Boosts grass",
                }
            ],
            flavor_text_entries=[
                {
                    "language": {"name": "en"},
                    "version_group": {"name": "ruby-sapphire"},
                    "flavor_text": "Powers up grass-type moves.",
                }
            ],
        )
        saved = SimpleNamespace(name="overgrow")
        ability_repository_mock.save.return_value = saved
        service = AbilityService(repository=ability_repository_mock, client=client)

        result = await service.get_or_create(
            resource={
                "url": "https://pokeapi.co/api/v2/ability/65/",
                "slot": 1,
                "is_hidden": True,
            }
        )

        assert result is saved
        saved_entity = ability_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.order == 65
        assert saved_entity.slot == 1
        assert saved_entity.is_hidden is True
