from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.exceptions import AppHTTPException
from app.domain.trainer.schema import CapturePayloadSchema, OnboardPayloadSchema
from app.domain.trainer.service import TrainerService
from app.models import PokemonStatusEnum, RoleEnum


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.save = AsyncMock()
    repository.find_by = AsyncMock()
    return repository


def _build_trainer() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        owned_pokemons=[],
        pokedex=None,
        known_encounters=[],
        party_slots=[],
        status=PokemonStatusEnum.INCOMPLETE,
    )


def _build_trainer_with_pokeballs(pokeballs: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        pokeballs=pokeballs,
        capture_rate=75,
        owned_pokemons=[],
        pokedex=None,
        known_encounters=[],
        party_slots=[],
        status=PokemonStatusEnum.INCOMPLETE,
    )


def _build_owned_pokemon() -> SimpleNamespace:
    return SimpleNamespace(
        captured_at="2024-01-01T00:00:00Z",
        pokemon=SimpleNamespace(encounters=[SimpleNamespace(id=uuid4(), order=1)]),
    )


def _build_capture_payload(pokemon_name: str = 'bulbasaur', nickname: str | None = None) -> CapturePayloadSchema:
    return CapturePayloadSchema(pokemon_name=pokemon_name, nickname=nickname)


@pytest.mark.asyncio
async def test_from_session_builds_service() -> None:
    service = TrainerService.from_session(AsyncMock())
    assert isinstance(service, TrainerService)


def test_init_builds_default_dependencies_from_session(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    with (
        patch(
            "app.domain.trainer.service.OwnedPokemonService.from_session"
        ) as owned_from_session,
        patch(
            "app.domain.trainer.service.PokemonService.from_session"
        ) as pokemon_from_session,
        patch(
            "app.domain.trainer.service.PokedexService.from_session"
        ) as pokedex_from_session,
        patch(
            "app.domain.trainer.service.TrainerEncounterService.from_session"
        ) as encounter_from_session,
        patch(
            "app.domain.trainer.service.TrainerPartyService.from_session"
        ) as party_from_session,
    ):
        owned_from_session.return_value = AsyncMock()
        pokemon_from_session.return_value = AsyncMock()
        pokedex_from_session.return_value = AsyncMock()
        encounter_from_session.return_value = AsyncMock()
        party_from_session.return_value = AsyncMock()

        TrainerService(repository=repository)

        owned_from_session.assert_called_once_with(trainer_session)
        pokemon_from_session.assert_called_once_with(trainer_session)
        pokedex_from_session.assert_called_once_with(trainer_session)
        encounter_from_session.assert_called_once_with(trainer_session)
        party_from_session.assert_called_once_with(trainer_session)


@pytest.mark.asyncio
async def test_onboard_uses_existing_trainer_when_user_is_already_onboarded(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    repository.find_by = AsyncMock(side_effect=[trainer, trainer])
    owned_pokemon_service = AsyncMock()
    owned_pokemon_service.get_or_create = AsyncMock(return_value=_build_owned_pokemon())
    pokedex_service = AsyncMock()
    pokedex_service.get_or_create = AsyncMock()
    trainer_encounter_service = AsyncMock()
    trainer_encounter_service.get_or_create_list = AsyncMock()
    trainer_party_service = AsyncMock()
    trainer_party_service.get_or_create_list = AsyncMock()
    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_pokemon_service,
        pokemon_service=AsyncMock(),
        pokedex_service=pokedex_service,
        trainer_encounter_service=trainer_encounter_service,
        trainer_party_service=trainer_party_service,
    )
    user = SimpleNamespace(
        id=uuid4(), trainer=SimpleNamespace(id=trainer.id), role=RoleEnum.USER
    )

    result = await service.onboard(user, OnboardPayloadSchema(pokemon_name="bulbasaur"))

    assert result is trainer
    repository.find_by.assert_awaited()
    owned_pokemon_service.get_or_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_onboard_raises_when_trainer_is_already_onboarded(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer.status = PokemonStatusEnum.COMPLETE
    repository = _build_repository(trainer_session)
    repository.find_by = AsyncMock(return_value=trainer)
    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    user = SimpleNamespace(
        id=uuid4(), trainer=SimpleNamespace(id=trainer.id), role=RoleEnum.USER
    )

    with pytest.raises(AppHTTPException, match="already onboarded"):
        await service.onboard(user, OnboardPayloadSchema(pokemon_name="bulbasaur"))


@pytest.mark.asyncio
async def test_onboard_sets_status_complete_when_trainer_already_has_pokemon(
    trainer_session: AsyncMock,
) -> None:
    owned_pokemon = _build_owned_pokemon()
    trainer = _build_trainer()
    trainer.owned_pokemons = [owned_pokemon]
    repository = _build_repository(trainer_session)
    repository.save.return_value = trainer
    repository.find_by = AsyncMock(return_value=trainer)
    pokedex_service = AsyncMock()
    pokedex_service.get_or_create = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    trainer_encounter_service = AsyncMock()
    trainer_encounter_service.get_or_create_list = AsyncMock(
        return_value=[SimpleNamespace(id=uuid4())]
    )
    trainer_party_service = AsyncMock()
    trainer_party_service.get_or_create_list = AsyncMock(
        return_value=[SimpleNamespace(id=uuid4())]
    )
    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=pokedex_service,
        trainer_encounter_service=trainer_encounter_service,
        trainer_party_service=trainer_party_service,
    )
    service.cache_service.delete_domain = AsyncMock()
    user = SimpleNamespace(
        id=uuid4(), trainer=SimpleNamespace(id=trainer.id), role=RoleEnum.USER
    )

    result = await service.onboard(user, OnboardPayloadSchema(pokemon_name="bulbasaur"))

    assert result is trainer
    assert trainer.status == PokemonStatusEnum.COMPLETE


@pytest.mark.asyncio
async def test_onboard_rejects_invalid_starter_for_regular_user(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    repository.save.return_value = trainer
    owned_pokemon_service = AsyncMock()
    owned_pokemon_service.get_or_create = AsyncMock(
        side_effect=HTTPException(status_code=400, detail="Pokemon are not allowed")
    )
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=owned_pokemon_service,
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid4(), trainer=None, role=RoleEnum.USER)

    with pytest.raises(AppHTTPException, match="Pokemon are not allowed"):
        await service.onboard(user, OnboardPayloadSchema(pokemon_name="pikachu"))


@pytest.mark.asyncio
async def test_onboard_returns_none_when_repository_save_returns_none(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.save.return_value = None
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid4(), trainer=None, role=RoleEnum.USER)

    with pytest.raises(AppHTTPException, match="Cannot onboard trainer, try again later!"):
        await service.onboard(user, OnboardPayloadSchema(pokemon_name="bulbasaur"))


@pytest.mark.asyncio
async def test_onboard_happy_path_for_admin(trainer_session: AsyncMock) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    repository.save.return_value = trainer
    repository.find_by.return_value = trainer
    owned_pokemon = _build_owned_pokemon()
    owned_pokemon_service = AsyncMock()
    owned_pokemon_service.get_or_create.return_value = owned_pokemon
    pokedex_service = AsyncMock()
    pokedex_service.get_or_create = AsyncMock()
    trainer_encounter_service = AsyncMock()
    trainer_encounter_service.get_or_create_list = AsyncMock()
    trainer_party_service = AsyncMock()
    trainer_party_service.get_or_create_list = AsyncMock()

    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_pokemon_service,
        pokemon_service=AsyncMock(),
        pokedex_service=pokedex_service,
        trainer_encounter_service=trainer_encounter_service,
        trainer_party_service=trainer_party_service,
    )
    service.cache_service.delete_domain = AsyncMock()

    user = SimpleNamespace(id=uuid4(), trainer=None, role=RoleEnum.ADMIN)
    payload = OnboardPayloadSchema(
        pokemon_name="  mew  ", nickname="M", pokeballs=10, capture_rate=150
    )

    result = await service.onboard(user, payload)

    assert result.id == trainer.id
    owned_pokemon_service.get_or_create.assert_awaited_once()
    pokedex_service.get_or_create.assert_awaited_once()
    trainer_encounter_service.get_or_create_list.assert_awaited_once()
    trainer_party_service.get_or_create_list.assert_awaited_once()
    trainer_session.commit.assert_awaited_once()
    trainer_session.refresh.assert_awaited_once_with(trainer)
    service.cache_service.delete_domain.assert_awaited_once()


@pytest.mark.asyncio
async def test_onboard_raises_when_created_trainer_cannot_be_reloaded(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    repository.save.return_value = trainer
    repository.find_by.return_value = None
    owned_pokemon = _build_owned_pokemon()
    owned_pokemon_service = AsyncMock()
    owned_pokemon_service.get_or_create.return_value = owned_pokemon

    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_pokemon_service,
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )

    with (
        patch(
            "app.domain.trainer.service.handle_service_exception"
        ) as handle_exception,
        pytest.raises(RuntimeError, match="handled"),
    ):
        handle_exception.side_effect = RuntimeError("handled")
        user = SimpleNamespace(id=uuid4(), trainer=None, role=RoleEnum.USER)
        await service.onboard(user, OnboardPayloadSchema(pokemon_name="bulbasaur"))

    trainer_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_onboard_rolls_back_and_delegates_exception_handler(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    repository.save.side_effect = RuntimeError("db-error")
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid4(), trainer=None, role=RoleEnum.USER)

    with (
        patch(
            "app.domain.trainer.service.handle_service_exception"
        ) as handle_exception,
        pytest.raises(RuntimeError, match="handled"),
    ):
        handle_exception.side_effect = RuntimeError("handled")
        await service.onboard(user, OnboardPayloadSchema(pokemon_name="bulbasaur"))

    trainer_session.rollback.assert_awaited_once()
    handle_exception.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_trainer_by_user_context(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    expected = _build_trainer()
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=expected)
    trainer_id = uuid4()

    result = await service.get_or_create(
        user_id=uuid4(),
        is_admin=False,
        trainer=SimpleNamespace(id=trainer_id),
        payload=OnboardPayloadSchema(pokemon_name="bulbasaur"),
    )

    assert result is expected
    service.find_by.assert_awaited_once_with(id=trainer_id, user_id=ANY)
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_builds_trainer_with_admin_payload_values(
    trainer_session: AsyncMock,
) -> None:
    repository = _build_repository(trainer_session)
    expected = _build_trainer()
    repository.save.return_value = expected
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )

    result = await service.get_or_create(
        user_id=uuid4(),
        is_admin=True,
        trainer=None,
        payload=OnboardPayloadSchema(
            pokemon_name="mew",
            pokeballs=10,
            capture_rate=150,
        ),
    )

    assert result is expected
    repository.save.assert_awaited_once()
    saved_entity = repository.save.await_args.kwargs["entity"]
    assert saved_entity.pokeballs == 10
    assert saved_entity.capture_rate == 150


@pytest.mark.asyncio
async def test_capture_raises_when_user_has_no_trainer(trainer_session: AsyncMock) -> None:
    repository = _build_repository(trainer_session)
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid4(), trainer=None, role=RoleEnum.USER)

    with pytest.raises(HTTPException) as exc_info:
        await service.capture(current_user=user, payload=_build_capture_payload())

    assert exc_info.value.status_code == 400
    assert 'onboarded' in exc_info.value.detail


@pytest.mark.asyncio
async def test_capture_raises_when_trainer_has_no_pokeballs(trainer_session: AsyncMock) -> None:
    trainer = _build_trainer_with_pokeballs(pokeballs=0)
    repository = _build_repository(trainer_session)
    service = TrainerService(
        repository=repository,
        owned_pokemon_service=AsyncMock(),
        pokemon_service=AsyncMock(),
        pokedex_service=AsyncMock(),
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid4(), trainer=trainer, role=RoleEnum.USER)

    with pytest.raises(HTTPException) as exc_info:
        await service.capture(current_user=user, payload=_build_capture_payload())

    assert exc_info.value.status_code == 400
    assert 'pokeballs' in exc_info.value.detail


@pytest.mark.asyncio
async def test_capture_decrements_pokeballs_and_returns_trainer(trainer_session: AsyncMock) -> None:
    trainer = _build_trainer_with_pokeballs(pokeballs=3)
    updated_trainer = _build_trainer_with_pokeballs(pokeballs=2)
    updated_trainer.id = trainer.id

    fresh_trainer = _build_trainer_with_pokeballs(pokeballs=2)
    fresh_trainer.id = trainer.id

    repository = _build_repository(trainer_session)
    repository.update = AsyncMock(return_value=updated_trainer)
    repository.find_by = AsyncMock(return_value=fresh_trainer)

    pokedex_entry = SimpleNamespace(hp=30, max_hp=100)
    pokedex_service = AsyncMock()
    pokedex_service.discover = AsyncMock(return_value=pokedex_entry)

    owned_pokemon = SimpleNamespace(
        id=uuid4(),
        pokemon=SimpleNamespace(encounters=[]),
    )
    owned_pokemon_service = AsyncMock()
    owned_pokemon_service.create = AsyncMock(return_value=owned_pokemon)

    trainer_encounter_service = AsyncMock()
    trainer_encounter_service.update_list = AsyncMock()

    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_pokemon_service,
        pokemon_service=AsyncMock(),
        pokedex_service=pokedex_service,
        trainer_encounter_service=trainer_encounter_service,
        trainer_party_service=AsyncMock(),
    )

    user = SimpleNamespace(id=uuid4(), trainer=trainer, role=RoleEnum.USER)
    result = await service.capture(
        current_user=user,
        payload=_build_capture_payload(pokemon_name='bulbasaur', nickname='Bulba'),
    )

    assert result is fresh_trainer
    assert trainer.pokeballs == 2
    repository.update.assert_awaited_once_with(trainer)
    pokedex_service.discover.assert_awaited_once_with(
        name='bulbasaur',
        trainer=updated_trainer,
        without_throw=True,
    )
    owned_pokemon_service.create.assert_awaited_once_with(
        nickname='Bulba',
        trainer=updated_trainer,
        pokedex_hp=pokedex_entry.hp,
        pokemon_name='bulbasaur',
        pokedex_max_hp=pokedex_entry.max_hp,
        trainer_capture_rate=updated_trainer.capture_rate,
    )
    trainer_encounter_service.update_list.assert_awaited_once_with(
        trainer=updated_trainer,
        encounters=owned_pokemon.pokemon.encounters,
    )
    repository.find_by.assert_awaited_once_with(id=updated_trainer.id)


@pytest.mark.asyncio
async def test_capture_returns_reloaded_trainer_after_all_operations(trainer_session: AsyncMock) -> None:
    trainer = _build_trainer_with_pokeballs(pokeballs=1)
    updated_trainer = SimpleNamespace(id=trainer.id, pokeballs=0, capture_rate=75)
    fresh_trainer = SimpleNamespace(id=trainer.id, pokeballs=0)

    repository = _build_repository(trainer_session)
    repository.update = AsyncMock(return_value=updated_trainer)
    repository.find_by = AsyncMock(return_value=fresh_trainer)

    pokedex_entry = SimpleNamespace(hp=10, max_hp=50)
    pokedex_service = AsyncMock()
    pokedex_service.discover = AsyncMock(return_value=pokedex_entry)

    owned_pokemon = SimpleNamespace(pokemon=SimpleNamespace(encounters=[]))
    owned_pokemon_service = AsyncMock()
    owned_pokemon_service.create = AsyncMock(return_value=owned_pokemon)

    service = TrainerService(
        repository=repository,
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_pokemon_service,
        pokemon_service=AsyncMock(),
        pokedex_service=pokedex_service,
        trainer_encounter_service=AsyncMock(),
        trainer_party_service=AsyncMock(),
    )

    user = SimpleNamespace(id=uuid4(), trainer=trainer, role=RoleEnum.USER)
    result = await service.capture(
        current_user=user,
        payload=_build_capture_payload(),
    )

    assert result is fresh_trainer
