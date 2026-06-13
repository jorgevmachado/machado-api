from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.trainer.trainer_log.repository import TrainerLogRepository
from app.domain.trainer.trainer_log.schema import (
    TrainerLogSchema,
)
from app.models import (
    TrainerLog,
    LogTypeEnum,
    LogStatusEnum,
    TrainerLogEventEnum,
    OwnedPokemon,
    Pokedex,
    TrainerEncounter,
    TrainerParty,
)

logger = logging.getLogger(__name__)


def _serialize_value(value):
    """Recursively convert UUIDs and datetimes to strings."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value


class TrainerLogService(BaseService[TrainerLogRepository, TrainerLog]):
    def __init__(
        self,
        repository: TrainerLogRepository,
    ) -> None:
        super().__init__(
            alias="TrainerLog",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="TrainerLogService",
                operation="trainer.trainer_log",
            ),
            schema_class=TrainerLogSchema,
            cache_prefix="trainer_log",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerLogRepository(session))

    async def create(
        self,
        log_type: LogTypeEnum,
        event: TrainerLogEventEnum,
        user_id: UUID,
        message: str | None = None,
        payload: dict | None = None,
        status: LogStatusEnum | None = None,
        trainer_id: UUID | None = None,
        pokedex: Pokedex | None = None,
        trainer_parties: list[TrainerParty] | None = None,
        trainer_encounters: list[TrainerEncounter] | None = None,
        owned_pokemon: OwnedPokemon | None = None,
    ) -> TrainerLog:
        current_payload = {"user_id": str(user_id), **(payload or {})}
        entity = TrainerLog(
            type=log_type,
            event=event,
            payload=current_payload,
            message="",
            status=LogStatusEnum.SUCCESS,
            trainer_id=trainer_id,
        )

        if log_type == LogTypeEnum.TRAINER:
            if not status:
                status = LogStatusEnum.SUCCESS if trainer_id else LogStatusEnum.ERROR
            entity.status = status

        if log_type == LogTypeEnum.POKEMON:
            if not status:
                status = LogStatusEnum.SUCCESS if owned_pokemon else LogStatusEnum.ERROR
            entity.status = status
            if owned_pokemon:
                entity.payload = {
                    "name": owned_pokemon.pokemon.name,
                    "nickname": owned_pokemon.nickname,
                    "captured_at": owned_pokemon.captured_at.isoformat()
                    if owned_pokemon.captured_at
                    else None,
                    **current_payload,
                }

        if log_type == LogTypeEnum.POKEDEX:
            if not status:
                status = LogStatusEnum.SUCCESS if pokedex else LogStatusEnum.ERROR
            entity.status = status
            if pokedex:
                entries = pokedex.entries
                selected = next((item for item in entries if item.discovered), None)
                entity.payload = {
                    "total": len(entries),
                    "pokedex_id": str(pokedex.id),
                    "pokemon_name": selected.name if selected else None,
                    "discovered_at": selected.discovered_at.isoformat()
                    if selected
                    else None,
                    **current_payload,
                }

        if log_type == LogTypeEnum.ENCOUNTER:
            if not status:
                status = (
                    LogStatusEnum.SUCCESS if trainer_encounters else LogStatusEnum.ERROR
                )
            entity.status = status
            if trainer_encounters:
                selected = next(
                    (item for item in trainer_encounters if item.is_active), None
                )
                entity.payload = {
                    "total": len(trainer_encounters),
                    "active_encounter": str(selected.pokemon_encounter_id)
                    if selected
                    else None,
                    **current_payload,
                }

        if log_type == LogTypeEnum.PARTY:
            if not status:
                status = (
                    LogStatusEnum.SUCCESS if trainer_parties else LogStatusEnum.ERROR
                )
            entity.status = status
            if trainer_parties:
                active_pokemons = [
                    item.owned_pokemon.name
                    if item.owned_pokemon
                    else str(item.owned_pokemon_id)
                    for item in trainer_parties
                    if item.is_active
                ]
                entity.payload = {
                    "total": len(trainer_parties),
                    "active_pokemons": active_pokemons,
                    **current_payload,
                }

        if not message:
            status_message = (
                "error" if status == LogStatusEnum.ERROR else "successfully"
            )
            message = f"{log_type} {event} {status_message}"
        entity.message = message

        # Ensure all payload values are JSON-serializable
        entity.payload = _serialize_value(entity.payload)

        return await self.repository.save(entity=entity)
