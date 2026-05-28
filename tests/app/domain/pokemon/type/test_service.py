from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.type.schema import TypeSyncResourceSchema
from app.domain.pokemon.type.service import TypeService
from app.models import PokemonStatusEnum


class TestTypeService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resources_creates_and_updates_damages(
        type_repository_mock: AsyncMock,
        type_sync_resource: TypeSyncResourceSchema,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        updated_type = SimpleNamespace(name="grass")
        service.get_or_create = AsyncMock(return_value=type_sync_resource)
        service.update_damages = AsyncMock(return_value=updated_type)

        result = await service.sync_from_resources(
            [{"type": {"name": "grass", "url": "https://pokeapi.co/api/v2/type/12/"}}]
        )

        assert result == [updated_type]
        service.update_damages.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resources_skips_when_get_or_create_returns_none(
        type_repository_mock: AsyncMock,
        type_sync_resource: TypeSyncResourceSchema,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service.get_or_create = AsyncMock(side_effect=[None, type_sync_resource])
        service.update_damages = AsyncMock(return_value=SimpleNamespace(name="grass"))

        result = await service.sync_from_resources(
            [
                {
                    "type": {
                        "name": "missing",
                        "url": "https://pokeapi.co/api/v2/type/0/",
                    }
                },
                {
                    "type": {
                        "name": "grass",
                        "url": "https://pokeapi.co/api/v2/type/12/",
                    }
                },
            ]
        )

        assert len(result) == 1
        service.update_damages.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_type(
        type_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="grass")
        type_repository_mock.find_by.return_value = existing
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        result = await service.get_or_create(order=12)

        assert result is not None
        assert result.type is existing

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_raises_without_name(
        type_repository_mock: AsyncMock,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="Name cannot be None"):
            await service.get_or_create(order=12)

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_raises_when_external_type_is_missing(
        type_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_type.return_value = None
        service = TypeService(repository=type_repository_mock, client=client)

        with pytest.raises(ValueError, match="Failed to retrieve external type"):
            await service.get_or_create(order=12, name="grass", url="url")

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_without_damage_relations(
        type_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_type.return_value = SimpleNamespace(
            move_damage_class=None,
            sprites=None,
            damage_relations=None,
        )
        saved = SimpleNamespace(name="grass")
        type_repository_mock.save.return_value = saved
        service = TypeService(repository=type_repository_mock, client=client)
        service._update_description = AsyncMock(return_value="desc")

        result = await service.get_or_create(order=12, name="grass", url="url")

        assert result is not None
        assert result.type is saved
        assert result.type_strengths == []
        assert result.type_weaknesses == []

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_with_damage_relations(
        type_repository_mock: AsyncMock,
    ) -> None:
        damage_relations = {
            "double_damage_from": [
                {"name": "water", "url": "https://pokeapi.co/api/v2/type/11/"}
            ],
            "half_damage_from": [],
            "double_damage_to": [
                {"name": "fire", "url": "https://pokeapi.co/api/v2/type/10/"}
            ],
            "half_damage_to": [],
        }
        client = AsyncMock()
        client.get_type.return_value = SimpleNamespace(
            move_damage_class=SimpleNamespace(
                url="https://pokeapi.co/api/v2/move-damage-class/3/"
            ),
            sprites=None,
            damage_relations=damage_relations,
        )
        saved = SimpleNamespace(name="grass")
        type_repository_mock.save.return_value = saved
        service = TypeService(repository=type_repository_mock, client=client)
        service._update_description = AsyncMock(return_value="desc")

        result = await service.get_or_create(order=12, name="grass", url="url")

        assert result is not None
        assert result.type is saved
        assert [item.name for item in result.type_weaknesses] == ["water"]
        assert [item.name for item in result.type_strengths] == ["fire"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_empty_relations_when_business_returns_none(
        type_repository_mock: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client = AsyncMock()
        client.get_type.return_value = SimpleNamespace(
            move_damage_class=None,
            sprites=None,
            damage_relations={},
        )
        saved = SimpleNamespace(name="grass")
        type_repository_mock.save.return_value = saved
        service = TypeService(repository=type_repository_mock, client=client)
        service._update_description = AsyncMock(return_value="desc")
        monkeypatch.setattr(
            "app.domain.pokemon.type.service.ensure_damage_relations",
            lambda _damage_relations: None,
        )

        result = await service.get_or_create(order=12, name="grass", url="url")

        assert result is not None
        assert result.type is saved
        assert result.type_weaknesses == []
        assert result.type_strengths == []

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_description_returns_given_description(
        type_repository_mock: AsyncMock,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        result = await service._update_description(
            type_class_url="url", description="already"
        )

        assert result == "already"

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_description_returns_empty_without_url(
        type_repository_mock: AsyncMock,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        result = await service._update_description(type_class_url=None)

        assert result == ""

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_description_reads_external_description(
        type_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_move_damage_class_by_url.return_value = SimpleNamespace(
            descriptions=[{"language": {"name": "en"}, "description": "special moves"}]
        )
        service = TypeService(repository=type_repository_mock, client=client)

        result = await service._update_description(
            "https://pokeapi.co/api/v2/move-damage-class/3/"
        )

        assert result == "special moves"

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_description_returns_empty_when_external_is_missing(
        type_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_move_damage_class_by_url.return_value = None
        service = TypeService(repository=type_repository_mock, client=client)

        result = await service._update_description(
            "https://pokeapi.co/api/v2/move-damage-class/3/"
        )

        assert result == ""

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_damages_updates_entity_and_marks_complete(
        type_repository_mock: AsyncMock,
        type_entity: SimpleNamespace,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        type_repository_mock.update.return_value = type_entity
        service.sync_from_damages = AsyncMock(
            side_effect=[
                [SimpleNamespace(name="fire")],
                [SimpleNamespace(name="water")],
            ]
        )

        result = await service.update_damages(
            resource=type_entity,
            type_strengths=[
                SimpleNamespace(name="fire", url="https://pokeapi.co/api/v2/type/10/")
            ],
            type_weaknesses=[
                SimpleNamespace(name="water", url="https://pokeapi.co/api/v2/type/11/")
            ],
        )

        assert result is type_entity
        assert type_entity.status == PokemonStatusEnum.COMPLETE
        type_repository_mock.update.assert_awaited_once_with(type_entity)

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_damages_returns_same_entity_when_no_changes(
        type_repository_mock: AsyncMock,
        type_entity: SimpleNamespace,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service.sync_from_damages = AsyncMock(side_effect=[[], []])

        result = await service.update_damages(
            resource=type_entity,
            type_strengths=[],
            type_weaknesses=[],
        )

        assert result is type_entity
        type_repository_mock.update.assert_not_awaited()

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_damages_collects_existing_resources(
        type_repository_mock: AsyncMock,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service.get_or_create = AsyncMock(
            side_effect=[
                TypeSyncResourceSchema(type=SimpleNamespace(name="fire")),
                None,
            ]
        )

        result = await service.sync_from_damages(
            [
                SimpleNamespace(name="fire", url="https://pokeapi.co/api/v2/type/10/"),
                SimpleNamespace(
                    name="unknown", url="https://pokeapi.co/api/v2/type/0/"
                ),
            ]
        )

        assert [item.name for item in result] == ["fire"]
