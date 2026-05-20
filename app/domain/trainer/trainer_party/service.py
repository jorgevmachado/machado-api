from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.trainer.trainer_party.business import validate_party_selection
from app.domain.trainer.trainer_party.repository import TrainerPartyRepository
from app.domain.trainer.trainer_party.schema import (
    TrainerPartyMemberSchema,
    UpdateTrainerPartySchema,
)
from app.models import MyPokemon, TrainerParty, User
from app.models.common import utcnow

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class TrainerPartyService(
    BaseService[TrainerPartyRepository, TrainerParty, TrainerPartyMemberSchema]
):
    def __init__(
        self,
        repository: TrainerPartyRepository,
        trainer_service: TrainerService | None = None,
    ) -> None:
        super().__init__(
            alias="TrainerParty",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="TrainerPartyService",
                operation="trainer_party",
            ),
            schema_class=TrainerPartyMemberSchema,
            cache_prefix="trainer",
        )
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        self.party_cache_service = CacheService(
            alias="TrainerParty",
            prefix="trainer",
            logger_params=self.logger_params,
            schema_class=TrainerPartyMemberSchema,
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerPartyRepository(session))

    def _party_key(self, trainer_id: str) -> str:
        return self.party_cache_service.cache.build_key("trainer", "party", trainer_id)

    async def _get_trainer_or_404(self, current_user: User):
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        return trainer

    async def _invalidate_party_cache(self, trainer_id: str) -> None:
        await self.party_cache_service.cache.delete_cache(self._party_key(trainer_id))

    async def update_party(
        self,
        current_user: User,
        payload: UpdateTrainerPartySchema,
    ) -> list[TrainerPartyMemberSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        validate_party_selection(payload.my_pokemon_ids)
        my_pokemons = await self.repository.list_owned_my_pokemon(
            trainer.id,
            payload.my_pokemon_ids,
        )
        if len(my_pokemons) != len(payload.my_pokemon_ids):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer party contains invalid Pokemon",
            )
        my_pokemon_by_id = {entity.id: entity for entity in my_pokemons}
        ordered_party: list[MyPokemon] = [
            my_pokemon_by_id[my_pokemon_id] for my_pokemon_id in payload.my_pokemon_ids
        ]
        await self.repository.soft_delete_active_party(trainer.id, utcnow())
        await self.repository.create_party(
            trainer_id=trainer.id,
            my_pokemons=ordered_party,
        )
        await self.repository.session.commit()
        await self._invalidate_party_cache(str(trainer.id))
        await self.trainer_service.invalidate_home_cache(str(trainer.id))
        return await self.get_party_by_trainer_id(trainer.id)

    async def get_party(self, current_user: User) -> list[TrainerPartyMemberSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        return await self.get_party_by_trainer_id(trainer.id)

    async def get_party_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> list[TrainerPartyMemberSchema]:
        key = self._party_key(str(trainer_id))
        cached = await self.party_cache_service.get_list(key)
        if cached:
            return cached
        entities = await self.repository.list_active_party(trainer_id)
        serialized = [self.to_party_schema(entity) for entity in entities]
        await self.party_cache_service.set_list(key, serialized)
        return serialized

    @staticmethod
    def to_party_schema(entity) -> TrainerPartyMemberSchema:
        return TrainerPartyMemberSchema.model_validate(entity)
