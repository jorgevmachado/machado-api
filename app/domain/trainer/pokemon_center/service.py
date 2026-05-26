from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.manager import CacheManager
from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.trainer.battle.repository import BattleSessionRepository
from app.domain.trainer.battle.service import BattleSessionService
from app.domain.trainer.my_pokemon.repository import MyPokemonRepository
from app.domain.trainer.my_pokemon.service import MyPokemonService
from app.domain.trainer.pokemon_center.business import (
    build_healing_log_payload,
    resolve_healing_action_type,
)
from app.domain.trainer.pokemon_center.repository import PokemonCenterRepository
from app.domain.trainer.pokemon_center.schema import (
    HealingLogHistorySchema,
    LastHealingSummarySchema,
    PokemonCenterHealingResultSchema,
    PokemonCenterHealingSummarySchema,
)
from app.domain.trainer.trainer_party.repository import TrainerPartyRepository
from app.domain.trainer.trainer_party.service import TrainerPartyService
from app.models import HealingLog, MyPokemon, PokemonCenterHealing, Trainer
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class PokemonCenterService(
    BaseService[
        PokemonCenterRepository,
        PokemonCenterHealing,
        PokemonCenterHealingSummarySchema,
    ]
):
    def __init__(
        self,
        repository: PokemonCenterRepository,
        *,
        trainer_party_service: TrainerPartyService,
        my_pokemon_service: MyPokemonService,
        battle_session_service: BattleSessionService,
    ) -> None:
        super().__init__(
            alias="PokemonCenterHealing",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="PokemonCenterService",
                operation="pokemon_center_healing",
            ),
            schema_class=PokemonCenterHealingSummarySchema,
            cache_prefix="trainer",
        )
        self.trainer_party_service = trainer_party_service
        self.my_pokemon_service = my_pokemon_service
        self.battle_session_service = battle_session_service
        self.cache = CacheManager()
        self.history_cache_service = CacheService(
            alias="HealingHistory",
            prefix="trainer",
            logger_params=self.logger_params,
            schema_class=HealingLogHistorySchema,
        )

    @classmethod
    def from_session(cls, session: AsyncSession) -> "PokemonCenterService":
        trainer_party_service = TrainerPartyService(TrainerPartyRepository(session))
        return cls(
            PokemonCenterRepository(session),
            trainer_party_service=trainer_party_service,
            my_pokemon_service=MyPokemonService(MyPokemonRepository(session)),
            battle_session_service=BattleSessionService(
                BattleSessionRepository(session),
                trainer_party_service=trainer_party_service,
            ),
        )

    def _history_key(
        self,
        *,
        trainer_id: UUID,
        page_filter: Annotated[FilterPage, Query()] | None = None,
    ) -> str:
        return self.history_cache_service.cache.build_key(
            "trainer",
            "healing",
            FilterPage.build(page_filter, trainer_id=str(trainer_id)).model_dump(),
        )

    async def invalidate_history_cache(self, trainer_id: str) -> None:
        await self.cache.delete_pattern(f"trainer:healing:*trainer_id={trainer_id}*")

    async def get_latest_summary(self, trainer_id: UUID) -> LastHealingSummarySchema | None:
        entity = await self.repository.find_latest_by_trainer_id(trainer_id)
        if entity is None:
            return None
        return LastHealingSummarySchema.model_validate(entity)

    async def heal_party(self, trainer: Trainer) -> PokemonCenterHealingResultSchema:
        try:
            if await self.battle_session_service.has_active_battle(trainer.id):
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="Pokemon Center healing is unavailable during an active battle",
                )

            party_entities = await self.trainer_party_service.repository.list_active_party(trainer.id)
            if not party_entities:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Trainer has no active party",
                )

            restored_logs: list[HealingLog] = []
            restored_context: list[tuple[HealingLog, MyPokemon]] = []
            total_restored_hp = 0
            total_restored_pp = 0

            for party_slot in party_entities:
                healing_result = self.my_pokemon_service.apply_full_healing(party_slot.my_pokemon)
                if not healing_result["changed"]:
                    continue

                restored_hp = int(healing_result["restored_hp"])
                restored_pp = int(healing_result["restored_pp"])
                was_revived = bool(healing_result["was_revived"])
                total_restored_hp += restored_hp
                total_restored_pp += restored_pp

                log_entry = HealingLog(
                    trainer_id=trainer.id,
                    pokemon_center_healing_id=UUID(int=0),
                    my_pokemon_id=party_slot.my_pokemon.id,
                    action_type=resolve_healing_action_type(was_revived=was_revived),
                    payload=build_healing_log_payload(
                        my_pokemon=party_slot.my_pokemon,
                        restored_hp=restored_hp,
                        restored_pp=restored_pp,
                        was_revived=was_revived,
                    ),
                )
                restored_logs.append(log_entry)
                restored_context.append((log_entry, party_slot.my_pokemon))

            if not restored_logs:
                return PokemonCenterHealingResultSchema(
                    success=True,
                    message="Party is already fully healed",
                )

            summary = await self.repository.create_summary(
                PokemonCenterHealing(
                    trainer_id=trainer.id,
                    healed_pokemon_quantity=len(restored_logs),
                    restored_hp=total_restored_hp,
                    restored_pp=total_restored_pp,
                )
            )
            for log in restored_logs:
                log.pokemon_center_healing_id = summary.id
            await self.repository.create_logs(restored_logs)
            await self.repository.session.commit()

            restored_entries: list[HealingLogHistorySchema] = []
            for log, my_pokemon in restored_context:
                restored_entries.append(
                    HealingLogHistorySchema.model_validate(
                        {
                            "id": log.id,
                            "trainer_id": log.trainer_id,
                            "pokemon_center_healing_id": log.pokemon_center_healing_id,
                            "my_pokemon_id": log.my_pokemon_id,
                            "action_type": log.action_type,
                            "payload": log.payload,
                            "created_at": log.created_at,
                            "updated_at": log.updated_at,
                            "deleted_at": log.deleted_at,
                            "my_pokemon": my_pokemon,
                        }
                    )
                )

            await self.cache.delete_cache(self.cache.build_key("trainer", "home", str(trainer.id)))
            await self.cache.delete_cache(self.cache.build_key("trainer", "party", str(trainer.id)))
            await self.cache.delete_pattern(f"my_pokemon:*trainer_id={trainer.id}*")
            await self.invalidate_history_cache(str(trainer.id))

            return PokemonCenterHealingResultSchema(
                success=True,
                message="Pokemon Center healing completed successfully",
                healing_summary=PokemonCenterHealingSummarySchema.model_validate(summary),
                restored_pokemon=restored_entries,
            )
        except Exception:
            await self.repository.session.rollback()
            raise

    async def list_history(
        self,
        trainer: Trainer,
        page_filter: Annotated[FilterPage, Query()] | None = None,
    ):
        key = self._history_key(trainer_id=trainer.id, page_filter=page_filter)
        cached = await self.history_cache_service.get_list(key)
        if cached:
            return cached

        history = await self.repository.list_history(
            trainer_id=trainer.id,
            page_filter=page_filter,
        )
        if isinstance(history, list):
            serialized = [HealingLogHistorySchema.model_validate(entry) for entry in history]
            await self.history_cache_service.set_list(key, serialized)
            return serialized

        serialized_items = [HealingLogHistorySchema.model_validate(entry) for entry in history.items]
        serialized_page = history.model_copy(update={"items": serialized_items})
        await self.history_cache_service.set_list(key, serialized_page)
        return serialized_page
