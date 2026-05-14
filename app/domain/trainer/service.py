from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.my_pokemon.business import (
    DEFAULT_TRAINER_CAPTURE_RATE,
    DEFAULT_TRAINER_POKEBALLS,
    STARTER_POKEMON_NAMES,
)
from app.domain.my_pokemon.repository import MyPokemonRepository
from app.domain.trainer.repository import TrainerRepository
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingResponseSchema,
    TrainerSchema,
)
from app.models import Trainer, User
from app.models.enums import RoleEnum


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.my_pokemon.service import MyPokemonService


class TrainerService(BaseService[TrainerRepository, Trainer]):
    def __init__(
            self,
            repository: TrainerRepository,
            my_pokemon_service: MyPokemonService | None = None,
    ) -> None:
        super().__init__(
            alias="Trainer",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="TrainerService", operation="trainer"
            ),
            schema_class=TrainerSchema,
        )
        if my_pokemon_service is None:
            from app.domain.my_pokemon.service import MyPokemonService

            my_pokemon_service = MyPokemonService(
                MyPokemonRepository(repository.session),
                trainer_service=self,
            )
        self.my_pokemon_service = my_pokemon_service

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerRepository(session))

    async def get_by_user_id(self, user_id: UUID) -> Trainer | None:
        return await self.repository.find_by(user_id=user_id)

    async def create(
        self, *, user_id: UUID, pokeballs: int, capture_rate: int
    ) -> Trainer:
        return await self.repository.save(
            entity=Trainer(
                user_id=user_id,
                pokeballs=pokeballs,
                capture_rate=capture_rate,
            )
        )

    async def onboard(
        self,
        current_user: User,
        payload: OnboardingTrainerSchema,
    ) -> TrainerOnboardingResponseSchema:
        try:
            existing_trainer = await self.get_by_user_id(current_user.id)
            if existing_trainer is not None:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="Trainer already initialized",
                )

            pokemon_name = payload.pokemon_name.strip().lower()
            is_admin = current_user.role == RoleEnum.ADMIN
            if not is_admin and pokemon_name not in STARTER_POKEMON_NAMES:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Starter Pokemon is not allowed",
                )

            trainer = await self.create(
                user_id=current_user.id,
                pokeballs=payload.pokeballs
                if is_admin and payload.pokeballs
                else DEFAULT_TRAINER_POKEBALLS,
                capture_rate=payload.capture_rate
                if is_admin and payload.capture_rate
                else DEFAULT_TRAINER_CAPTURE_RATE,
            )
            created = await self.my_pokemon_service.create_owned_for_trainer(
                trainer_id=trainer.id,
                pokemon_name=pokemon_name,
                nickname=payload.nickname,
                commit=False,
            )
            await self.repository.session.commit()
            return TrainerOnboardingResponseSchema(
                id=trainer.id,
                user_id=trainer.user_id,
                pokeballs=trainer.pokeballs,
                capture_rate=trainer.capture_rate,
                created_at=trainer.created_at,
                updated_at=trainer.updated_at,
                deleted_at=trainer.deleted_at,
                my_pokemons=[self.my_pokemon_service.to_schema(created)],
            )
        except Exception as exception:
            await self.repository.session.rollback()
            handle_service_exception(
                exception,
                logger=logger,
                service="TrainerService",
                operation="onboard",
                raise_exception=True,
            )
