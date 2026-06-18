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
from app.domain.trainer.battle.business import process_battle
from app.domain.trainer.battle.service import BattleService
from app.domain.trainer.business import (
    DEFAULT_TRAINER_CAPTURE_RATE,
    DEFAULT_TRAINER_POKEBALLS,
    STARTER_POKEMON_NAMES,
)
from app.domain.trainer.encounter.service import TrainerEncounterService
from app.domain.trainer.exploration.service import ExplorationService
from app.domain.trainer.owned_pokemon.service import OwnedPokemonService
from app.domain.trainer.party.service import TrainerPartyService
from app.domain.trainer.pokedex.service import PokedexService
from app.domain.trainer.repository import TrainerRepository
from app.domain.trainer.schema import (
    OnboardPayloadSchema,
    TrainerSchema,
    CapturePayloadSchema,
    FightPayloadSchema,
)
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    RoleEnum,
    Trainer,
    User,
    LogStatusEnum,
    TrainerLogEventEnum,
    LogTypeEnum,
    PokemonStatusEnum,
    ExplorationEvent,
    BattleSession,
)
from app.models.enums import ExplorationEventTypeEnum, BattleSessionStatusEnum

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
        battle_service: BattleService | None = None,
        exploration_service: ExplorationService | None = None,
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
        self.battle_service = battle_service or BattleService.from_session(session)
        self.exploration_service = (
            exploration_service or ExplorationService.from_session(session)
        )

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
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Cannot onboard trainer, try again later!",
                )

            if trainer.status == PokemonStatusEnum.COMPLETE:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Trainer is already onboarded",
                )
            owned_pokemons = trainer.owned_pokemons
            owned_pokemon = owned_pokemons[0] if owned_pokemons else None
            if not owned_pokemon:
                owned_pokemon = await self.owned_pokemon_service.get_or_create(
                    commit=False,
                    nickname=payload.nickname,
                    trainer=trainer,
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
                trainer=trainer,
                discovered_at=owned_pokemon.captured_at,
                discovered_pokemon=owned_pokemon.pokemon,
            )

            trainer_encounters = (
                await self.trainer_encounter_service.get_or_create_list(
                    trainer=trainer,
                    encounters=owned_pokemon.pokemon.encounters,
                )
            )

            trainer_parties = await self.trainer_party_service.get_or_create_list(
                trainer=trainer,
                owned_pokemon=owned_pokemon,
            )

            if owned_pokemons and pokedex and trainer_encounters and trainer_parties:
                trainer.status = PokemonStatusEnum.COMPLETE

            await self.repository.update(trainer)

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

        created_trainer = await self.repository.save(
            entity=Trainer(
                user_id=user_id,
                status=PokemonStatusEnum.INCOMPLETE,
                pokeballs=pokeballs,
                capture_rate=capture_rate,
                base_capture_rate=DEFAULT_TRAINER_CAPTURE_RATE,
                capture_progress_points=0,
            )
        )

        await self.trainer_log.create(
            event=TrainerLogEventEnum.CREATED,
            user_id=user_id,
            trainer_id=created_trainer.id if created_trainer else None,
            log_type=LogTypeEnum.TRAINER,
            payload={
                "is_admin": is_admin,
            },
        )

        return created_trainer

    async def capture(
        self, current_user: User, payload: CapturePayloadSchema
    ) -> Trainer | None:
        trainer = await self._validate_trainer(
            user=current_user,
            message="User must be onboarded to capture a pokemon",
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
            trainer=trainer,
            without_throw=True,
        )

        owned_pokemon = await self.owned_pokemon_service.create(
            nickname=payload.nickname,
            trainer=trainer,
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
            trainer=trainer,
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

    async def explore(self, current_user: User) -> ExplorationEvent:
        trainer = await self._validate_trainer(
            user=current_user,
            message="User must be onboarded to explore a pokemon word",
        )

        active_battle = await self.battle_service.find_by(
            status=BattleSessionStatusEnum.ACTIVE,
            trainer_id=trainer.id,
            without_throw=True,
        )

        if active_battle:
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.EXPLORED,
                user_id=current_user.id,
                message="Trainer already has an active battle",
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Trainer already has an active battle",
            )

        active_encounter = await self.trainer_encounter_service.active(
            trainer_id=trainer.id
        )
        if active_encounter is None:
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.EXPLORED,
                user_id=current_user.id,
                message="Trainer has no active encounter",
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer has no active encounter",
            )
        exploration_result = await self.exploration_service.exploration(
            trainer=trainer,
            trainer_encounter=active_encounter,
        )
        if exploration_result.event_type == ExplorationEventTypeEnum.WILD_POKEMON:
            trainer_party = await self.trainer_party_service.ready_to_battle(
                trainer=trainer
            )

            battle_session = await self.battle_service.create_or_resume(
                party=trainer_party,
                trainer=trainer,
                exploration_event=exploration_result,
            )
            exploration_result.payload = {
                **exploration_result.payload,
                "trainer_pokemon_id": str(trainer_party.owned_pokemon.id),
                "trainer_pokemon_name": trainer_party.owned_pokemon.name,
                "battle_session_id": str(battle_session.id),
                "battle_status": getattr(
                    battle_session.status, "value", battle_session.status
                ),
                "has_active_battle": True,
            }
            exploration_result = await self.exploration_service.update_result(
                exploration_event=exploration_result
            )

        if exploration_result.event_type == ExplorationEventTypeEnum.POKEBALLS:
            trainer.pokeballs = exploration_result.payload["trainer_pokeballs"]
            await self.repository.update(entity=trainer)
        payload = exploration_result.payload
        payload["event_type"] = exploration_result.event_type
        await self.trainer_log.create(
            status=LogStatusEnum.SUCCESS,
            event=TrainerLogEventEnum.EXPLORED,
            user_id=current_user.id,
            message="User explored a Pokémon world",
            payload=payload,
            log_type=LogTypeEnum.TRAINER,
        )
        await self.cache_service.delete_domain()
        return exploration_result

    async def fight(
        self, current_user: User, payload: FightPayloadSchema
    ) -> BattleSession:
        trainer = await self._validate_trainer(
            user=current_user, message="User must be onboarded to fight"
        )

        battle_session = await self.battle_service.get(
            trainer=trainer,
            battle_id=payload.battle_id,
        )

        owned_pokemon_move_id = payload.owned_pokemon_move_id

        pokedex_entry = await self.pokedex_service.find_one_cached(
            param=str(battle_session.wild_pokemon_id),
            trainer_id=trainer.id,
            user_request=current_user.username,
            clean_cache=True,
        )

        trainer_party_battle = await self.trainer_party_service.preparation_for_battle(
            trainer=trainer,
            owned_pokemon_id=battle_session.trainer_active_owned_pokemon_id,
            owned_pokemon_move_id=owned_pokemon_move_id,
        )

        trainer_party = trainer_party_battle.trainer_party
        trainer_party_selected_move = trainer_party_battle.trainer_party_selected_move

        battle_result = process_battle(
            move=trainer_party_selected_move.pokemon_move,
            status=battle_session.status,
            wild_pokemon=pokedex_entry,
            trainer_party=trainer_party,
        )

        if battle_result.error:
            return await self.battle_service.persist(
                wild_pokemon=pokedex_entry,
                trainer_party=trainer_party,
                battle_result=battle_result,
                battle_session=battle_session,
            )

        updated_trainer_party = await self.trainer_party_service.update_after_battle(
            trainer=trainer,
            trainer_party=trainer_party,
            selected_pokemon_progression=battle_result.owned_pokemon_progression,
        )

        updated_wild_pokemon = await self.pokedex_service.update_after_battle(
            trainer=trainer,
            pokedex_entry=pokedex_entry,
            pokedex_entry_progression=battle_result.wild_pokemon_progression,
        )

        return await self.battle_service.persist(
            wild_pokemon=updated_wild_pokemon,
            trainer_party=updated_trainer_party,
            battle_result=battle_result,
            battle_session=battle_session,
        )

    async def _validate_trainer(
        self, user: User, message: str = "Trainer Not Found"
    ) -> Trainer:
        trainer = user.trainer
        if not trainer:
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.EXPLORED,
                user_id=user.id,
                message=message,
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                detail=message,
                status_code=HTTPStatus.BAD_REQUEST,
            )
        return trainer
