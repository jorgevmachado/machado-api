from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.service import CacheService
from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.trainer.my_pokemon.business import (
    DEFAULT_TRAINER_CAPTURE_RATE,
    DEFAULT_TRAINER_POKEBALLS,
    STARTER_POKEMON_NAMES,
)
from app.domain.trainer.my_pokemon.repository import MyPokemonRepository
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.repository import TrainerRepository
from app.domain.trainer.trainer_exploration.repository import TrainerExplorationRepository
from app.domain.trainer.trainer_exploration.schema import TrainerHomeSchema
from app.domain.trainer.trainer_party.repository import TrainerPartyRepository
from app.domain.trainer.trainer_party.service import TrainerPartyService
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingResponseSchema,
    TrainerSchema,
)
from app.models import Trainer, User
from app.models.enums import RoleEnum


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.my_pokemon import MyPokemonService
    from app.domain.trainer.pokedex.service import PokedexService
    from app.domain.trainer.trainer_exploration import TrainerExplorationService


class TrainerService(BaseService[TrainerRepository, Trainer]):
    def __init__(
        self,
        repository: TrainerRepository,
        my_pokemon_service: MyPokemonService | None = None,
        pokedex_service: PokedexService | None = None,
        trainer_exploration_service: TrainerExplorationService | None = None,
        trainer_party_service: TrainerPartyService | None = None,
    ) -> None:
        super().__init__(
            alias="Trainer",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="TrainerService", operation="trainer"
            ),
            schema_class=TrainerSchema,
            cache_prefix="trainer",
        )
        if my_pokemon_service is None:
            from app.domain.trainer.my_pokemon import MyPokemonService

            my_pokemon_service = MyPokemonService(
                MyPokemonRepository(repository.session),
                trainer_service=self,
            )
        if pokedex_service is None:
            from app.domain.trainer.pokedex.service import PokedexService

            pokedex_service = PokedexService(
                PokedexRepository(repository.session),
                trainer_service=self,
            )
        if trainer_exploration_service is None:
            from app.domain.trainer.trainer_exploration import TrainerExplorationService

            trainer_exploration_service = TrainerExplorationService(
                TrainerExplorationRepository(repository.session),
                trainer_service=self,
            )
        if trainer_party_service is None:
            trainer_party_service = TrainerPartyService(
                TrainerPartyRepository(repository.session),
                trainer_service=self,
            )
        self.my_pokemon_service = my_pokemon_service
        self.pokedex_service = pokedex_service
        self.trainer_exploration_service = trainer_exploration_service
        self.trainer_party_service = trainer_party_service
        self.home_cache_service = CacheService(
            alias="TrainerHome",
            prefix="trainer",
            logger_params=self.logger_params,
            schema_class=TrainerHomeSchema,
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerRepository(session))

    def _home_key(self, trainer_id: str) -> str:
        return self.home_cache_service.cache.build_key("trainer", "home", trainer_id)

    async def get_by_user_id(self, user_id: UUID) -> Trainer | None:
        return await self.repository.find_by(user_id=user_id)

    async def invalidate_home_cache(self, trainer_id: str) -> None:
        await self.home_cache_service.cache.delete_cache(self._home_key(trainer_id))

    async def create(
        self,
        *,
        user_id: UUID,
        pokeballs: int,
        capture_rate: int,
        commit: bool = True,
    ) -> Trainer:
        entity = Trainer(
            user_id=user_id,
            pokeballs=pokeballs,
            capture_rate=capture_rate,
        )
        self.repository.session.add(entity)
        await self.repository.session.flush()
        if commit:
            await self.repository.session.commit()
            await self.repository.session.refresh(entity)
        return entity

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
                commit=False,
            )
            created = await self.my_pokemon_service.create_owned_for_trainer(
                trainer_id=trainer.id,
                pokemon_name=pokemon_name,
                nickname=payload.nickname,
                commit=False,
            )
            pokedex = await self.pokedex_service.initialize_for_trainer(
                trainer_id=trainer.id,
                discovered_pokemon_name=pokemon_name,
                discovered_at=created.captured_at,
                commit=False,
            )
            known_encounters = (
                await self.trainer_exploration_service.initialize_for_trainer(
                    trainer_id=trainer.id,
                    starter_pokemon_name=pokemon_name,
                    commit=False,
                )
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
                pokedex=[self.pokedex_service.to_schema(entry) for entry in pokedex],
                known_encounters=[
                    self.trainer_exploration_service.to_encounter_schema(entry)
                    for entry in known_encounters
                ],
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

    async def get_home(self, current_user: User) -> TrainerHomeSchema:
        trainer = await self.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        key = self._home_key(str(trainer.id))
        cached = await self.home_cache_service.get_one(key)
        if cached:
            return cached
        active_encounter = (
            await self.trainer_exploration_service.get_active_encounter_by_trainer_id(trainer.id)
        )
        party = await self.trainer_party_service.get_party_by_trainer_id(trainer.id)
        latest_discoveries = await self.pokedex_service.list_latest_discoveries(trainer.id)
        serialized = TrainerHomeSchema(
            trainer=TrainerSchema.model_validate(trainer),
            active_encounter=active_encounter,
            party=party,
            latest_discoveries=[
                PokedexSchema.model_validate(entry) for entry in latest_discoveries
            ],
        )
        await self.home_cache_service.set_one(key, serialized)
        return serialized
