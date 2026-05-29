from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.owned_pokemon.service import OwnedPokemonService


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.find_by = AsyncMock()
    return repository


def _build_pokemon(name: str = "bulbasaur", capture_rate: int = 45) -> SimpleNamespace:
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
        capture_rate=capture_rate,
    )


def test_from_session_builds_service() -> None:
    service = OwnedPokemonService.from_session(AsyncMock())
    assert isinstance(service, OwnedPokemonService)


@pytest.mark.asyncio
async def test_create_returns_fresh_entity_and_commits(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4(), name="bulbasaur")
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon())
    owned_pokemon_move_service = AsyncMock()
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=owned_pokemon_move_service,
    )
    service.list_all = AsyncMock(return_value=set())
    service.cache_service.delete_domain = AsyncMock()

    created = await service.create(
        trainer_id=uuid4(),
        pokemon_name="bulbasaur",
        nickname=None,
        pokedex_hp=None,
        pokedex_max_hp=None,
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
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon())
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value={"bulbasaur"})
    service.cache_service.delete_domain = AsyncMock()

    await service.create(
        trainer_id=uuid4(),
        pokemon_name="bulbasaur",
        nickname="  Bulba  ",
        pokedex_hp=None,
        pokedex_max_hp=None,
        commit=False,
    )

    trainer_session.commit.assert_not_awaited()
    trainer_session.refresh.assert_not_awaited()
    service.cache_service.delete_domain.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_raises_when_fresh_entity_is_missing(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = None
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon())
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())

    with pytest.raises(HTTPException, match="Could not load created Owned Pokemon"):
        await service.create(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            pokedex_hp=None,
            pokedex_max_hp=None,
            commit=True,
        )


@pytest.mark.asyncio
async def test_create_raises_when_pokemon_is_not_allowed(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock()
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )

    with pytest.raises(HTTPException, match="Pokemon are not allowed"):
        await service.create(
            trainer_id=uuid4(),
            pokemon_name=" Bulbasaur ",
            nickname=None,
            pokedex_hp=None,
            pokedex_max_hp=None,
            commit=True,
            only_allowed_pokemon=["pikachu"],
        )

    pokemon_service.find_one.assert_not_awaited()
    trainer_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_raises_when_base_pokemon_does_not_exist(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=None)
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )

    with pytest.raises(HTTPException, match="Pokemon not found"):
        await service.create(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            pokedex_hp=None,
            pokedex_max_hp=None,
            commit=True,
        )

    trainer_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_rolls_back_when_commit_enabled_and_exception_occurs(
    trainer_session: AsyncMock,
) -> None:
    trainer_session.flush.side_effect = RuntimeError("flush-error")
    repository = _build_repository(trainer_session)
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon())
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())

    with pytest.raises(RuntimeError, match="flush-error"):
        await service.create(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            pokedex_hp=None,
            pokedex_max_hp=None,
            commit=True,
        )

    trainer_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_does_not_rollback_when_commit_disabled_and_exception_occurs(
    trainer_session: AsyncMock,
) -> None:
    trainer_session.flush.side_effect = RuntimeError("flush-error")
    repository = _build_repository(trainer_session)
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon())
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())

    with pytest.raises(RuntimeError, match="flush-error"):
        await service.create(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            pokedex_hp=None,
            pokedex_max_hp=None,
            commit=False,
        )

    trainer_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_returns_first_from_prefetched_owned_pokemons() -> None:
    prefetched = SimpleNamespace(id=uuid4())
    service = OwnedPokemonService(
        repository=_build_repository(AsyncMock()),
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.pokemon_service.find_by = AsyncMock()

    result = await service.get_or_create(
        trainer_id=uuid4(),
        pokemon_name="bulbasaur",
        owned_pokemons=[prefetched],
    )

    assert result is prefetched
    service.pokemon_service.find_by.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_from_pokemon_service() -> None:
    existing = SimpleNamespace(id=uuid4())
    service = OwnedPokemonService(
        repository=_build_repository(AsyncMock()),
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.pokemon_service.find_by = AsyncMock(return_value=existing)
    service.pokemon_service.list_all_cached = AsyncMock()

    result = await service.get_or_create(
        trainer_id=uuid4(),
        pokemon_name="bulbasaur",
        owned_pokemons=[],
    )

    assert result is existing
    service.pokemon_service.list_all_cached.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_creates_when_existing_owned_pokemon_is_missing() -> None:
    created = SimpleNamespace(id=uuid4())
    service = OwnedPokemonService(
        repository=_build_repository(AsyncMock()),
        pokemon_service=AsyncMock(),
        owned_pokemon_move_service=AsyncMock(),
    )
    service.pokemon_service.find_by = AsyncMock(return_value=None)
    service.pokemon_service.list_all_cached = AsyncMock()
    service.create = AsyncMock(return_value=created)

    result = await service.get_or_create(
        trainer_id=uuid4(),
        pokemon_name="bulbasaur",
        nickname="bulba",
        commit=False,
        only_allowed_pokemon=["bulbasaur"],
    )

    assert result is created
    service.pokemon_service.list_all_cached.assert_awaited_once_with(page_filter=ANY)
    service.create.assert_awaited_once_with(
        commit=False,
        nickname="bulba",
        trainer_id=ANY,
        pokemon_name="bulbasaur",
        only_allowed_pokemon=["bulbasaur"],
    )


@pytest.mark.asyncio
async def test_create_passes_trainer_capture_rate_to_validate(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.find_by.return_value = SimpleNamespace(id=uuid4(), name="bulbasaur")
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon())
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())
    service.cache_service.delete_domain = AsyncMock()

    with patch(
        "app.domain.trainer.owned_pokemon.service.validate_capture_rate"
    ) as mock_validate:
        await service.create(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            pokedex_hp=40,
            pokedex_max_hp=100,
            trainer_capture_rate=200,
            commit=True,
        )
        mock_validate.assert_called_once()
        call_kwargs = mock_validate.call_args.kwargs
        assert call_kwargs["pokedex_hp"] == 40
        assert call_kwargs["pokedex_max_hp"] == 100
        assert call_kwargs["trainer_capture_rate"] == 200


@pytest.mark.asyncio
async def test_create_raises_when_capture_rate_validation_fails(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    pokemon_service = AsyncMock()
    pokemon_service.find_one = AsyncMock(return_value=_build_pokemon(capture_rate=200))
    service = OwnedPokemonService(
        repository=repository,
        pokemon_service=pokemon_service,
        owned_pokemon_move_service=AsyncMock(),
    )
    service.list_all = AsyncMock(return_value=set())

    with pytest.raises(Exception):
        await service.create(
            trainer_id=uuid4(),
            pokemon_name="bulbasaur",
            nickname=None,
            pokedex_hp=100,
            pokedex_max_hp=100,
            trainer_capture_rate=50,
            commit=True,
        )


def test_init_builds_default_dependencies_from_session(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    with (
        patch(
            "app.domain.trainer.owned_pokemon.service.PokemonService.from_session"
        ) as pokemon_from_session,
        patch(
            "app.domain.trainer.owned_pokemon.service.OwnedPokemonMoveService.from_session"
        ) as move_from_session,
    ):
        pokemon_from_session.return_value = AsyncMock()
        move_from_session.return_value = AsyncMock()

        OwnedPokemonService(repository=repository)

        pokemon_from_session.assert_called_once_with(trainer_session)
        move_from_session.assert_called_once_with(trainer_session)
