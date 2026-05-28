from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.owned_pokemon.service import OwnedPokemonService


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.find_by = AsyncMock()
    return repository


def _build_pokemon(name: str = "bulbasaur") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        moves=[],
        hp=45,
        attack=49,
        defense=49,
        special_attack=65,
        special_defense=65,
        speed=45,
    )


def test_from_session_builds_service() -> None:
    service = OwnedPokemonService.from_session(AsyncMock())
    assert isinstance(service, OwnedPokemonService)


@pytest.mark.asyncio
async def test_create_returns_fresh_entity_and_commits(trainer_session: AsyncMock) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4(), name="bulbasaur")
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())
    service.cache_service.delete_domain = AsyncMock()

    pokemon = _build_pokemon()
    created = await service.create(
        trainer_id=uuid4(),
        pokemon=pokemon,
        nickname=None,
        commit=True,
    )

    assert created.name == "bulbasaur"
    trainer_session.add.assert_called_once()
    trainer_session.commit.assert_awaited_once()
    trainer_session.refresh.assert_awaited_once()
    service.owned_pokemon_move_service.sync_form_resources.assert_awaited_once()
    service.cache_service.delete_domain.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_without_commit_skips_commit_refresh_and_cache(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4(), name="bulbasaur")
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value={"bulbasaur"})
    service.cache_service.delete_domain = AsyncMock()
    pokemon = _build_pokemon()

    await service.create(
        trainer_id=uuid4(),
        pokemon=pokemon,
        nickname="  Bulba  ",
        commit=False,
    )

    trainer_session.commit.assert_not_awaited()
    trainer_session.refresh.assert_not_awaited()
    service.cache_service.delete_domain.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_raises_when_fresh_entity_is_missing(trainer_session: AsyncMock) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = None
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())
    pokemon = _build_pokemon()

    with pytest.raises(HTTPException, match="Could not load created Owned Pokemon"):
        await service.create(
            trainer_id=uuid4(),
            pokemon=pokemon,
            nickname=None,
            commit=True,
        )


@pytest.mark.asyncio
async def test_create_rolls_back_when_commit_enabled_and_exception_occurs(
    trainer_session: AsyncMock,
) -> None:
    trainer_session.flush.side_effect = RuntimeError("flush-error")
    repository = _build_repository(trainer_session)
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())
    pokemon = _build_pokemon()

    with pytest.raises(RuntimeError, match="flush-error"):
        await service.create(
            trainer_id=uuid4(),
            pokemon=pokemon,
            nickname=None,
            commit=True,
        )

    trainer_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_does_not_rollback_when_commit_disabled_and_exception_occurs(
    trainer_session: AsyncMock,
) -> None:
    trainer_session.flush.side_effect = RuntimeError("flush-error")
    repository = _build_repository(trainer_session)
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())
    pokemon = _build_pokemon()

    with pytest.raises(RuntimeError, match="flush-error"):
        await service.create(
            trainer_id=uuid4(),
            pokemon=pokemon,
            nickname=None,
            commit=False,
        )

    trainer_session.rollback.assert_not_awaited()


def test_init_builds_default_dependencies_from_session(trainer_session: AsyncMock) -> None:
    repository = _build_repository(trainer_session)
    with (
        patch("app.domain.trainer.owned_pokemon.service.PokemonService.from_session") as pokemon_from_session,
        patch("app.domain.trainer.owned_pokemon.service.OwnedPokemonMoveService.from_session") as move_from_session,
    ):
        pokemon_from_session.return_value = AsyncMock()
        move_from_session.return_value = AsyncMock()

        OwnedPokemonService(repository=repository)

        pokemon_from_session.assert_called_once_with(trainer_session)
        move_from_session.assert_called_once_with(trainer_session)
