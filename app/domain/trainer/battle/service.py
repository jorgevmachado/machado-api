from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.battle.battle_log.service import BattleLogService
from app.domain.trainer.battle.business import (
    build_trainer_party_snapshot,
    build_wild_pokemon_snapshot,
)
from app.domain.trainer.battle.repository import BattleRepository
from app.domain.trainer.battle.schema import (
    BattleSchema,
)
from app.domain.trainer.pokedex.service import PokedexService
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    BattleSession,
    ExplorationEvent,
    Trainer,
    TrainerParty,
)
from app.models.enums import BattleSessionStatusEnum

logger = logging.getLogger(__name__)


class BattleService(BaseService[BattleRepository, BattleSession]):
    def __init__(
        self,
        repository: BattleRepository,
        trainer_log: TrainerLogService | None = None,
        pokedex_service: PokedexService | None = None,
        battle_log_service: BattleLogService | None = None,
    ) -> None:
        super().__init__(
            alias="Battle",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="BattleService",
                operation="trainer.battle",
            ),
            schema_class=BattleSchema,
            cache_prefix="battle",
        )
        session = repository.session
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)
        self.pokedex_service = pokedex_service or PokedexService.from_session(session)
        self.battle_log_service = battle_log_service or BattleLogService.from_session(
            session
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(BattleRepository(session))

    async def create_or_resume(
        self,
        party: TrainerParty,
        trainer: Trainer,
        exploration_event: ExplorationEvent,
    ) -> BattleSession:
        active = await self.find_by(
            trainer_id=trainer.id,
            status=BattleSessionStatusEnum.ACTIVE,
            without_throw=True,
        )
        if active is not None:
            return active

        trainer_party_snapshot = build_trainer_party_snapshot(party)

        wild_pokemon_name = exploration_event.payload["wild_pokemon_name"]
        wild_pokemon = await self.pokedex_service.find_one_cached(
            param=wild_pokemon_name, trainer_id=trainer.id
        )

        wild_pokemon_snapshot = build_wild_pokemon_snapshot(wild_pokemon)

        entity = await self.repository.save(
            entity=BattleSession(
                status=BattleSessionStatusEnum.ACTIVE,
                trainer_id=trainer.id,
                wild_pokemon_id=wild_pokemon.id,
                wild_pokemon_name=wild_pokemon.name,
                wild_pokemon_level=wild_pokemon.level,
                exploration_event_id=exploration_event.id,
                wild_pokemon_snapshot=wild_pokemon_snapshot,
                trainer_party_snapshot=trainer_party_snapshot,
                trainer_active_owned_pokemon_id=party.owned_pokemon.id,
            )
        )

        setattr(entity, "_trainer_context", trainer)
        await self.battle_log_service.start(
            battle_session_id=entity.id,
            payload={
                "pokemon_name": wild_pokemon.name,
                "exploration_event_id": str(exploration_event.id),
                "trainer_active_owned_pokemon_id": str(party.owned_pokemon.id),
            },
        )

        return entity
