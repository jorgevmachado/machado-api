from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.exploration.business import (
    choose_event_type,
    choose_wild_pokemon,
    build_pokeball_reward,
)

from app.domain.trainer.exploration.repository import ExplorationRepository
from app.domain.trainer.exploration.schema import (
    ExplorationSchema,
)
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    ExplorationEvent,
    ExplorationEventTypeEnum,
    LogStatusEnum,
    Trainer,
    TrainerLogEventEnum,
    LogTypeEnum,
    TrainerEncounter,
)

logger = logging.getLogger(__name__)


class ExplorationService(BaseService[ExplorationRepository, ExplorationEvent]):
    def __init__(
        self,
        repository: ExplorationRepository,
        trainer_log: TrainerLogService | None = None,
    ) -> None:
        super().__init__(
            alias="Exploration",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="ExplorationService",
                operation="trainer.battle.exploration",
            ),
            schema_class=ExplorationSchema,
            cache_prefix="exploration",
        )
        session = repository.session
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(ExplorationRepository(session))

    async def exploration(
        self,
        trainer: Trainer,
        trainer_encounter: TrainerEncounter,
    ) -> ExplorationEvent:
        event_type = choose_event_type()

        payload: dict = {
            "pokeballs_found": 0,
            "trainer_pokeballs": trainer.pokeballs,
            "trainer_encounter_id": str(trainer_encounter.id),
            "total_pokemon_found": len(trainer_encounter.pokemon_encounter.pokemons),
            "pokemon_encounter_id": str(trainer_encounter.pokemon_encounter_id),
            "pokemon_encounter_name": str(trainer_encounter.pokemon_encounter.name),
        }

        if event_type == ExplorationEventTypeEnum.WILD_POKEMON:
            pokemon = choose_wild_pokemon(trainer_encounter.pokemon_encounter.pokemons)
            payload["wild_pokemon_id"] = str(pokemon.id)
            payload["wild_pokemon_name"] = pokemon.name
        else:
            reward = build_pokeball_reward()
            payload["pokeballs_found"] = reward
            payload["trainer_pokeballs"] += reward

        entity = await self.repository.save(
            entity=ExplorationEvent(
                payload=payload,
                event_type=event_type,
                trainer_id=trainer.id,
            )
        )

        if not entity:
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.EXPLORED,
                user_id=trainer.user.id,
                message="Could not explore pokemon word",
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Could not explore pokemon word",
            )
        return entity

    async def update_result(
        self, exploration_event: ExplorationEvent
    ) -> ExplorationEvent:
        return await self.repository.update(entity=exploration_event)
