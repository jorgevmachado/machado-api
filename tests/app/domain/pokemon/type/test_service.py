from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.service.base import BaseService
from app.domain.pokemon.type.service import TypeService
from app.models import PokemonStatusEnum


class TestTypeService:
    @staticmethod
    def test_from_session_builds_service() -> None:
        service = TypeService.from_session(AsyncMock())

        assert isinstance(service, TypeService)

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_returns_entity_when_complete(
        type_repository_mock: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        type_entity: SimpleNamespace,
    ) -> None:
        type_entity.status = PokemonStatusEnum.COMPLETE
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        async def fake_super_find_one(
            _self: TypeService, _param: str, **_kwargs
        ) -> SimpleNamespace:
            return type_entity

        monkeypatch.setattr(BaseService, "find_one", fake_super_find_one)
        service._sync_external = AsyncMock()

        result = await service.find_one("12")

        assert result is type_entity
        service._sync_external.assert_not_awaited()

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_syncs_when_entity_is_incomplete(
        type_repository_mock: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        type_entity: SimpleNamespace,
    ) -> None:
        type_entity.status = PokemonStatusEnum.INCOMPLETE
        synced = SimpleNamespace(name="synced")
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        async def fake_super_find_one(
            _self: TypeService, _param: str, **_kwargs
        ) -> SimpleNamespace:
            return type_entity

        monkeypatch.setattr(BaseService, "find_one", fake_super_find_one)
        service._sync_external = AsyncMock(return_value=synced)

        result = await service.find_one("12")

        assert result is synced
        service._sync_external.assert_awaited_once_with(entity=type_entity)

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resources_reads_both_shapes(
        type_repository_mock: AsyncMock,
    ) -> None:
        first = SimpleNamespace(name="grass")
        second = SimpleNamespace(name="fire")
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service.get_or_create = AsyncMock(side_effect=[first, second])

        result = await service.sync_from_resources(
            [
                {"type": {"url": "https://pokeapi.co/api/v2/type/12/"}},
                {"url": "https://pokeapi.co/api/v2/type/10/"},
            ]
        )

        assert result == [first, second]
        assert service.get_or_create.await_count == 2
        service.get_or_create.assert_any_await(
            order=12, url="https://pokeapi.co/api/v2/type/12/"
        )
        service.get_or_create.assert_any_await(
            order=10, url="https://pokeapi.co/api/v2/type/10/"
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_external_requires_order(
        type_repository_mock: AsyncMock,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="Order is required"):
            await service._sync_external(url="https://pokeapi.co/api/v2/type/12/")

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_external_requires_url(type_repository_mock: AsyncMock) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="URL is required"):
            await service._sync_external(order=12)

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_external_raises_when_external_type_missing(
        type_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_type.return_value = None
        service = TypeService(repository=type_repository_mock, client=client)

        with pytest.raises(ValueError, match="Failed to retrieve external type"):
            await service._sync_external(
                order=12,
                url="https://pokeapi.co/api/v2/type/12/",
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_external_returns_existing_entity_without_damages(
        type_repository_mock: AsyncMock,
        type_entity: SimpleNamespace,
    ) -> None:
        client = AsyncMock()
        client.get_type.return_value = SimpleNamespace(
            name="grass",
            move_damage_class=None,
            sprites=None,
            damage_relations={},
        )
        service = TypeService(repository=type_repository_mock, client=client)

        result = await service._sync_external(entity=type_entity, with_damages=False)

        assert result is type_entity
        type_repository_mock.save.assert_not_awaited()

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_external_saves_and_adds_damage_relations(
        type_repository_mock: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client = AsyncMock()
        client.get_type.return_value = SimpleNamespace(
            name="grass",
            move_damage_class=SimpleNamespace(
                url="https://pokeapi.co/api/v2/move-damage-class/3/"
            ),
            sprites=SimpleNamespace(),
            damage_relations={"any": "value"},
        )
        saved = SimpleNamespace(name="grass")
        type_repository_mock.save.return_value = saved
        service = TypeService(repository=type_repository_mock, client=client)
        service._update_description = AsyncMock(return_value="desc")
        expected = SimpleNamespace(name="complete")
        service._add_damage_relations = AsyncMock(return_value=expected)

        monkeypatch.setattr(
            "app.domain.pokemon.type.service.ensure_badges",
            lambda _sprites: SimpleNamespace(
                badge_url="badge",
                badge_icon_url="icon",
                badge_shield_url="shield",
                badge_legends_url="legends",
                badge_shield_icon_url="shield-icon",
                badge_legend_icon_url="legend-icon",
            ),
        )
        monkeypatch.setattr(
            "app.domain.pokemon.type.service.ensure_colors",
            lambda _name: SimpleNamespace(text_color="#fff", background_color="#000"),
        )
        monkeypatch.setattr(
            "app.domain.pokemon.type.service.ensure_damage_relations",
            lambda _relations: SimpleNamespace(
                strengths=[
                    SimpleNamespace(
                        name="fire", url="https://pokeapi.co/api/v2/type/10/"
                    )
                ],
                weaknesses=[
                    SimpleNamespace(
                        name="water", url="https://pokeapi.co/api/v2/type/11/"
                    )
                ],
            ),
        )

        result = await service._sync_external(
            order=12,
            url="https://pokeapi.co/api/v2/type/12/",
        )

        assert result is expected
        type_repository_mock.save.assert_awaited_once()
        service._add_damage_relations.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_complete_entity(
        type_repository_mock: AsyncMock,
        type_entity: SimpleNamespace,
    ) -> None:
        type_entity.status = PokemonStatusEnum.COMPLETE
        type_repository_mock.find_by.return_value = type_entity
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service._sync_external = AsyncMock()

        result = await service.get_or_create(order=12)

        assert result is type_entity
        service._sync_external.assert_not_awaited()

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_syncs_when_missing(
        type_repository_mock: AsyncMock,
    ) -> None:
        type_repository_mock.find_by.return_value = None
        synced = SimpleNamespace(name="synced")
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service._sync_external = AsyncMock(return_value=synced)

        result = await service.get_or_create(
            order=12, url="https://pokeapi.co/api/v2/type/12/"
        )

        assert result is synced
        service._sync_external.assert_awaited_once_with(
            url="https://pokeapi.co/api/v2/type/12/",
            order=12,
            entity=None,
            with_damages=True,
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_add_damage_relations_updates_entity_and_marks_complete(
        type_repository_mock: AsyncMock,
        type_entity: SimpleNamespace,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        type_repository_mock.update.return_value = type_entity
        service._sync_from_damages = AsyncMock(
            side_effect=[
                [SimpleNamespace(name="fire")],
                [SimpleNamespace(name="water")],
            ]
        )

        result = await service._add_damage_relations(
            entity=type_entity,
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
    async def test_add_damage_relations_returns_same_entity_without_changes(
        type_repository_mock: AsyncMock,
        type_entity: SimpleNamespace,
    ) -> None:
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service._sync_from_damages = AsyncMock(side_effect=[[], []])

        result = await service._add_damage_relations(
            entity=type_entity,
            type_strengths=[],
            type_weaknesses=[],
        )

        assert result is type_entity
        type_repository_mock.update.assert_not_awaited()

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
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client = AsyncMock()
        client.get_move_damage_class_by_url.return_value = SimpleNamespace(
            descriptions=[{"language": {"name": "en"}, "description": "special moves"}]
        )
        service = TypeService(repository=type_repository_mock, client=client)
        monkeypatch.setattr(
            "app.domain.pokemon.type.service.get_text_language",
            lambda **_kwargs: SimpleNamespace(text="special moves"),
        )

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
    async def test_sync_from_damages_collects_existing_resources(
        type_repository_mock: AsyncMock,
    ) -> None:
        kept = SimpleNamespace(name="fire")
        service = TypeService(repository=type_repository_mock, client=AsyncMock())
        service.get_or_create = AsyncMock(side_effect=[kept, None])

        result = await service._sync_from_damages(
            [
                SimpleNamespace(name="fire", url="https://pokeapi.co/api/v2/type/10/"),
                SimpleNamespace(
                    name="unknown", url="https://pokeapi.co/api/v2/type/0/"
                ),
            ]
        )

        assert result == [kept]
        service.get_or_create.assert_any_await(
            url="https://pokeapi.co/api/v2/type/10/",
            order=10,
            with_damages=False,
        )
        service.get_or_create.assert_any_await(
            url="https://pokeapi.co/api/v2/type/0/",
            order=0,
            with_damages=False,
        )
