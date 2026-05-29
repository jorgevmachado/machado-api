from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.business import (
    DEFAULT_TRAINER_CAPTURE_RATE,
    DEFAULT_TRAINER_POKEBALLS,
    STARTER_POKEMON_NAMES,
)
from app.domain.trainer.encounter.service import TrainerEncounterService
from app.domain.trainer.owned_pokemon.service import OwnedPokemonService
from app.domain.trainer.party.service import TrainerPartyService
from app.domain.trainer.pokedex.service import PokedexService
from app.domain.trainer.repository import TrainerRepository
from app.domain.trainer.schema import OnboardPayloadSchema, TrainerSchema, CapturePayloadSchema
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    RoleEnum,
    Trainer,
    User,
    LogStatusEnum,
    TrainerLogEventEnum, LogTypeEnum,
)

logger = logging.getLogger(__name__)


class TrainerService(BaseService[TrainerRepository, Trainer]):
    def __init__(
        self,
        repository: TrainerRepository,
        trainer_log: TrainerLogService | None = None,
        owned_pokemon_service: OwnedPokemonService | None = None,
        pokemon_service: PokemonService | None = None,
        pokedex_service: PokedexService | None = None,
        trainer_encounter_service: TrainerEncounterService | None = None,
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
        session = repository.session
        self.owned_pokemon_service = (
            owned_pokemon_service or OwnedPokemonService.from_session(session)
        )
        self.pokemon_service = pokemon_service or PokemonService.from_session(session)
        self.pokedex_service = pokedex_service or PokedexService.from_session(session)
        self.trainer_party_service = (
            trainer_party_service or TrainerPartyService.from_session(session)
        )
        self.trainer_encounter_service = (
            trainer_encounter_service or TrainerEncounterService.from_session(session)
        )
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerRepository(session))

    async def onboard(
        self, current_user: User, payload: OnboardPayloadSchema
    ) -> Trainer | None:
        try:
            is_admin = current_user.role == RoleEnum.ADMIN
            trainer = await self.get_or_create(
                user_id=current_user.id,
                is_admin=is_admin,
                trainer=current_user.trainer,
                payload=payload,
            )
            if not trainer:
                await self.trainer_log.create(
                    event=TrainerLogEventEnum.CREATED,
                    status=LogStatusEnum.ERROR,
                    user_id=current_user.id,
                    log_type=LogTypeEnum.TRAINER,
                )
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Cannot onboard trainer, try again later!",
                )

            owned_pokemon = await self.owned_pokemon_service.get_or_create(
                commit=False,
                nickname=payload.nickname,
                trainer_id=trainer.id,
                owned_pokemons=trainer.owned_pokemons,
                pokemon_name=payload.pokemon_name,
                only_allowed_pokemon=None if is_admin else STARTER_POKEMON_NAMES,
            )
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CAPTURED,
                user_id=current_user.id,
                log_type=LogTypeEnum.POKEMON,
                trainer_id=trainer.id,
                owned_pokemon=owned_pokemon,
            )

            pokedex = await self.pokedex_service.get_or_create(
                commit=False,
                pokedex=trainer.pokedex,
                trainer_id=trainer.id,
                discovered_at=owned_pokemon.captured_at,
                discovered_pokemon=owned_pokemon.pokemon,
            )
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CREATED,
                user_id=current_user.id,
                pokedex=pokedex,
                log_type=LogTypeEnum.POKEDEX,
                trainer_id=trainer.id,
            )

            trainer_encounters = await self.trainer_encounter_service.get_or_create_list(
                trainer_id=trainer.id,
                encounters=owned_pokemon.pokemon.encounters,
                known_encounters=trainer.known_encounters,
            )

            await self.trainer_log.create(
                event=TrainerLogEventEnum.CREATED,
                user_id=current_user.id,
                log_type=LogTypeEnum.ENCOUNTER,
                trainer_id=trainer.id,
                trainer_encounters=trainer_encounters,
            )

            trainer_parties = await self.trainer_party_service.get_or_create_list(
                trainer_id=trainer.id,
                party_slots=trainer.party_slots,
                owned_pokemon=owned_pokemon,
            )
            
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CREATED,
                user_id=current_user.id,
                log_type=LogTypeEnum.PARTY,
                trainer_id=trainer.id,
                trainer_parties=trainer_parties                
            )

            await self.repository.session.commit()
            await self.repository.session.refresh(trainer)

            fresh = await self.repository.find_by(id=trainer.id)

            if fresh is None:
                await self.trainer_log.create(
                    event=TrainerLogEventEnum.SHOWN,
                    status=LogStatusEnum.ERROR,
                    user_id=current_user.id,
                    message="Could not load created Trainer",
                    log_type=LogTypeEnum.TRAINER,
                    trainer_id=trainer.id,
                )
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Could not load created Trainer",
                )
            await self.cache_service.delete_domain()

            return fresh

        except Exception as exception:
            await self.repository.session.rollback()
            handle_service_exception(
                exception,
                logger=logger,
                service="TrainerService",
                operation="onboard",
                raise_exception=True,
            )

    async def get_or_create(
        self,
        user_id: UUID,
        is_admin: bool,
        payload: OnboardPayloadSchema,
        trainer: Trainer | None = None,
    ) -> Trainer:
        if trainer:
            return await self.find_by(id=trainer.id, user_id=user_id)

        pokeballs = DEFAULT_TRAINER_POKEBALLS
        capture_rate = DEFAULT_TRAINER_CAPTURE_RATE
        if is_admin:
            pokeballs = payload.pokeballs or DEFAULT_TRAINER_POKEBALLS
            capture_rate = payload.capture_rate or DEFAULT_TRAINER_POKEBALLS

        return await self.repository.save(
            entity=Trainer(
                user_id=user_id,
                pokeballs=pokeballs,
                capture_rate=capture_rate,
                base_capture_rate=DEFAULT_TRAINER_CAPTURE_RATE,
                capture_progress_points=0,
            )
        )

    async def capture(self, current_user: User, payload: CapturePayloadSchema) -> Trainer | None:
        trainer = current_user.trainer
        if not trainer:
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.CAPTURED,
                user_id=current_user.id,
                message="User must be onboarded to capture a pokemon",
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                detail="User must be onboarded to capture a pokemon",
                status_code=HTTPStatus.BAD_REQUEST,
            )        
        if trainer.pokeballs <= 0:
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CAPTURED,
                status=LogStatusEnum.ERROR,
                user_id=current_user.id,
                message="Trainer has no pokeballs left",
                log_type=LogTypeEnum.TRAINER,
                trainer_id=trainer.id,
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer has no pokeballs left",
            )
        trainer.pokeballs -= 1
        trainer = await self.repository.update(trainer)
        
        pokedex = await self.pokedex_service.discover(
            name=payload.pokemon_name,
            trainer_id=trainer.id,
            without_throw=True,
        )

        owned_pokemon = await self.owned_pokemon_service.create(
            nickname=payload.nickname,
            trainer_id=trainer.id,
            pokedex_hp=pokedex.hp,
            pokemon_name=payload.pokemon_name,
            pokedex_max_hp=pokedex.max_hp,
            trainer_capture_rate=trainer.capture_rate,
        )

        await self.trainer_log.create(
            event=TrainerLogEventEnum.CAPTURED,
            user_id=current_user.id,
            log_type=LogTypeEnum.POKEMON,
            trainer_id=trainer.id,
            owned_pokemon=owned_pokemon,
        )
        
        trainer_encounters = await self.trainer_encounter_service.update_list(
            trainer_id=trainer.id,
            encounters=owned_pokemon.pokemon.encounters,
        )

        await self.trainer_log.create(
            event=TrainerLogEventEnum.UPDATED,
            user_id=current_user.id,
            log_type=LogTypeEnum.ENCOUNTER,
            trainer_id=trainer.id,
            trainer_encounters=trainer_encounters,
        )

        return await self.repository.find_by(id=trainer.id)

