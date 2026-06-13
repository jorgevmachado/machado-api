from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.trainer.trainer_log.service import TrainerLogService, _serialize_value
from app.models import LogStatusEnum, LogTypeEnum, TrainerLogEventEnum


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.save = AsyncMock(side_effect=lambda entity: entity)
    return repository


def _build_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _build_service() -> TrainerLogService:
    return TrainerLogService(repository=_build_repository(_build_session()))


# --- _serialize_value tests ---


def test_serialize_value_converts_uuid_to_string() -> None:
    uid = uuid4()
    result = _serialize_value(uid)
    assert result == str(uid)
    assert isinstance(result, str)


def test_serialize_value_converts_list_of_uuids() -> None:
    uids = [uuid4(), uuid4()]
    result = _serialize_value(uids)
    assert result == [str(u) for u in uids]


def test_serialize_value_converts_dict_values() -> None:
    uid = uuid4()
    result = _serialize_value({"key": uid, "plain": "value"})
    assert result == {"key": str(uid), "plain": "value"}


def test_serialize_value_returns_plain_values_unchanged() -> None:
    assert _serialize_value("hello") == "hello"
    assert _serialize_value(42) == 42
    assert _serialize_value(None) is None


# --- from_session ---


def test_from_session_builds_service() -> None:
    service = TrainerLogService.from_session(AsyncMock())
    assert isinstance(service, TrainerLogService)


# --- create() for TRAINER type ---


@pytest.mark.asyncio
async def test_create_trainer_log_success_with_trainer_id() -> None:
    service = _build_service()
    trainer_id = uuid4()

    entity = await service.create(
        log_type=LogTypeEnum.TRAINER,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
        trainer_id=trainer_id,
    )

    assert entity.status == LogStatusEnum.SUCCESS
    assert entity.type == LogTypeEnum.TRAINER


@pytest.mark.asyncio
async def test_create_trainer_log_error_without_trainer_id() -> None:
    service = _build_service()

    entity = await service.create(
        log_type=LogTypeEnum.TRAINER,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
    )

    assert entity.status == LogStatusEnum.ERROR


# --- create() for POKEMON type ---


@pytest.mark.asyncio
async def test_create_pokemon_log_with_owned_pokemon() -> None:
    service = _build_service()
    captured_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    owned_pokemon = SimpleNamespace(
        pokemon=SimpleNamespace(name="bulbasaur"),
        nickname="Bulba",
        captured_at=captured_at,
    )

    entity = await service.create(
        log_type=LogTypeEnum.POKEMON,
        event=TrainerLogEventEnum.CAPTURED,
        user_id=uuid4(),
        owned_pokemon=owned_pokemon,
    )

    assert entity.status == LogStatusEnum.SUCCESS
    assert entity.payload["name"] == "bulbasaur"
    assert entity.payload["nickname"] == "Bulba"


@pytest.mark.asyncio
async def test_create_pokemon_log_without_owned_pokemon() -> None:
    service = _build_service()

    entity = await service.create(
        log_type=LogTypeEnum.POKEMON,
        event=TrainerLogEventEnum.CAPTURED,
        user_id=uuid4(),
    )

    assert entity.status == LogStatusEnum.ERROR


# --- create() for POKEDEX type ---


@pytest.mark.asyncio
async def test_create_pokedex_log_with_discovered_entry() -> None:
    service = _build_service()
    discovered_at = datetime(2024, 3, 1, tzinfo=timezone.utc)
    entry = SimpleNamespace(
        discovered=True, name="bulbasaur", discovered_at=discovered_at
    )
    pokedex = SimpleNamespace(id=uuid4(), entries=[entry])

    entity = await service.create(
        log_type=LogTypeEnum.POKEDEX,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
        pokedex=pokedex,
    )

    assert entity.status == LogStatusEnum.SUCCESS
    assert entity.payload["total"] == 1
    assert entity.payload["pokemon_name"] == "bulbasaur"
    assert entity.payload["discovered_at"] == discovered_at.isoformat()


@pytest.mark.asyncio
async def test_create_pokedex_log_with_no_discovered_entry() -> None:
    service = _build_service()
    entry = SimpleNamespace(discovered=False, name="bulbasaur", discovered_at=None)
    pokedex = SimpleNamespace(id=uuid4(), entries=[entry])

    entity = await service.create(
        log_type=LogTypeEnum.POKEDEX,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
        pokedex=pokedex,
    )

    assert entity.status == LogStatusEnum.SUCCESS
    assert entity.payload["pokemon_name"] is None
    assert entity.payload["discovered_at"] is None


@pytest.mark.asyncio
async def test_create_pokedex_log_without_pokedex() -> None:
    service = _build_service()

    entity = await service.create(
        log_type=LogTypeEnum.POKEDEX,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
    )

    assert entity.status == LogStatusEnum.ERROR


# --- create() for ENCOUNTER type ---


@pytest.mark.asyncio
async def test_create_encounter_log_with_active_encounter() -> None:
    service = _build_service()
    encounter_id = uuid4()
    encounters = [
        SimpleNamespace(is_active=True, pokemon_encounter_id=encounter_id),
        SimpleNamespace(is_active=False, pokemon_encounter_id=uuid4()),
    ]

    entity = await service.create(
        log_type=LogTypeEnum.ENCOUNTER,
        event=TrainerLogEventEnum.UPDATED,
        user_id=uuid4(),
        trainer_encounters=encounters,
    )

    assert entity.status == LogStatusEnum.SUCCESS
    assert entity.payload["total"] == 2
    assert entity.payload["active_encounter"] == str(encounter_id)


@pytest.mark.asyncio
async def test_create_encounter_log_without_encounters() -> None:
    service = _build_service()

    entity = await service.create(
        log_type=LogTypeEnum.ENCOUNTER,
        event=TrainerLogEventEnum.UPDATED,
        user_id=uuid4(),
    )

    assert entity.status == LogStatusEnum.ERROR


# --- create() for PARTY type ---


@pytest.mark.asyncio
async def test_create_party_log_with_active_parties() -> None:
    service = _build_service()
    parties = [
        SimpleNamespace(
            is_active=True,
            owned_pokemon=SimpleNamespace(name="Bulba"),
            owned_pokemon_id=uuid4(),
        ),
        SimpleNamespace(
            is_active=False,
            owned_pokemon=None,
            owned_pokemon_id=uuid4(),
        ),
    ]

    entity = await service.create(
        log_type=LogTypeEnum.PARTY,
        event=TrainerLogEventEnum.UPDATED,
        user_id=uuid4(),
        trainer_parties=parties,
    )

    assert entity.status == LogStatusEnum.SUCCESS
    assert entity.payload["total"] == 2
    assert "Bulba" in entity.payload["active_pokemons"]


@pytest.mark.asyncio
async def test_create_party_log_without_parties() -> None:
    service = _build_service()

    entity = await service.create(
        log_type=LogTypeEnum.PARTY,
        event=TrainerLogEventEnum.UPDATED,
        user_id=uuid4(),
    )

    assert entity.status == LogStatusEnum.ERROR


# --- custom message ---


@pytest.mark.asyncio
async def test_create_uses_custom_message_when_provided() -> None:
    service = _build_service()

    entity = await service.create(
        log_type=LogTypeEnum.TRAINER,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
        message="Custom message",
    )

    assert entity.message == "Custom message"


# --- payload with UUID value is serialized ---


@pytest.mark.asyncio
async def test_create_serializes_uuid_in_custom_payload() -> None:
    service = _build_service()
    raw_uuid = uuid4()

    entity = await service.create(
        log_type=LogTypeEnum.TRAINER,
        event=TrainerLogEventEnum.CREATED,
        user_id=uuid4(),
        payload={"ref_id": raw_uuid},
    )

    assert entity.payload["ref_id"] == str(raw_uuid)
    assert isinstance(entity.payload["ref_id"], str)
