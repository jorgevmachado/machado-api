from __future__ import annotations
import logging

from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.business import (
    STARTER_POKEMON_NAMES,
    DEFAULT_TRAINER_CAPTURE_RATE,
    DEFAULT_TRAINER_POKEBALLS,
)
from app.domain.trainer.encounter.service import TrainerEncounterService
from app.domain.trainer.owned_pokemon.service import OwnedPokemonService
from app.domain.trainer.pokedex.service import PokedexService

from app.models import Trainer, User, RoleEnum

from app.domain.trainer.repository import TrainerRepository
from app.domain.trainer.schema import TrainerSchema, OnboardPayloadSchema

logger = logging.getLogger(__name__)


class TrainerService(BaseService[TrainerRepository, Trainer]):
    def __init__(
        self,
        repository: TrainerRepository,
        owned_pokemon_service: OwnedPokemonService | None = None,
        pokemon_service: PokemonService | None = None,
        pokedex_service: PokedexService | None = None,
        trainer_encounter_service: TrainerEncounterService | None = None,
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
        session = repository.session
        self.owned_pokemon_service = (
            owned_pokemon_service or OwnedPokemonService.from_session(session)
        )
        self.pokemon_service = pokemon_service or PokemonService.from_session(session)
        self.pokedex_service = pokedex_service or PokedexService.from_session(session)
        self.trainer_encounter_service = (
            trainer_encounter_service or TrainerEncounterService.from_session(session)
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerRepository(session))

    async def onboard(
        self, current_user: User, payload: OnboardPayloadSchema
    ) -> Trainer | None:
        try:
            if current_user.trainer:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Trainer already onboarded",
                )
            is_admin = current_user.role == RoleEnum.ADMIN
            pokemon_name = payload.pokemon_name.strip().lower()

            if not is_admin and pokemon_name not in STARTER_POKEMON_NAMES:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Starter Pokemon is not allowed",
                )
            pokeballs = DEFAULT_TRAINER_POKEBALLS
            capture_rate = DEFAULT_TRAINER_CAPTURE_RATE
            if is_admin:
                pokeballs = payload.pokeballs or DEFAULT_TRAINER_POKEBALLS
                capture_rate = payload.capture_rate or DEFAULT_TRAINER_POKEBALLS

            trainer = await self.repository.save(
                entity=Trainer(
                    user_id=current_user.id,
                    pokeballs=pokeballs,
                    capture_rate=capture_rate,
                    base_capture_rate=DEFAULT_TRAINER_CAPTURE_RATE,
                    capture_progress_points=0,
                )
            )
            if trainer:
                pokemon = await self.pokemon_service.find_one(pokemon_name)
                if pokemon:
                    owned_pokemon = await self.owned_pokemon_service.create(
                        commit=False,
                        pokemon=pokemon,
                        nickname=payload.nickname,
                        trainer_id=trainer.id,
                    )

                    await self.pokedex_service.create(
                        commit=False,
                        trainer_id=trainer.id,
                        discovered_at=owned_pokemon.captured_at,
                        discovered_pokemon=owned_pokemon.pokemon,
                    )

                    await self.trainer_encounter_service.sync_from_resources(
                        trainer_id=trainer.id,
                        encounters=owned_pokemon.pokemon.encounters,
                    )
                    await self.repository.session.commit()
                    await self.repository.session.refresh(trainer)

                    fresh = await self.repository.find_by(id=trainer.id)

                    if fresh is None:
                        raise HTTPException(
                            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail="Could not load created Trainer",
                        )

                    await self.cache_service.delete_domain()

                    return fresh

            return trainer
        except Exception as exception:
            await self.repository.session.rollback()
            handle_service_exception(
                exception,
                logger=logger,
                service="TrainerService",
                operation="onboard",
                raise_exception=True,
            )
