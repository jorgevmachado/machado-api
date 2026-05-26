from __future__ import annotations

import logging
from math import floor, sqrt
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
from app.domain.trainer.pokemon_center.repository import PokemonCenterRepository
from app.domain.trainer.pokemon_center.schema import LastHealingSummarySchema
from app.domain.trainer.battle.repository import BattleSessionRepository
from app.domain.trainer.battle.schema import (
    BattleCaptureResultSchema,
    CaptureBattlePokemonSchema,
)
from app.domain.trainer.battle.service import BattleSessionService
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.repository import TrainerRepository
from app.domain.trainer.encounter.repository import TrainerEncounterRepository
from app.domain.trainer.encounter.schema import TrainerHomeSchema, TrainerEncounterSchema
from app.domain.trainer.trainer_party import TrainerPartyMemberSchema
from app.domain.trainer.trainer_party.repository import TrainerPartyRepository
from app.domain.trainer.trainer_party.service import TrainerPartyService
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingResponseSchema,
    TrainerSchema,
)
from app.models import Trainer, User, TrainerEncounter, TrainerParty, PokemonEncounter
from app.models.enums import BattleSessionStatusEnum, RoleEnum
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.my_pokemon import MyPokemonService
    from app.domain.trainer.pokedex.service import PokedexService
    from app.domain.trainer.encounter import TrainerEncounterService


class TrainerService(BaseService[TrainerRepository, Trainer]):
    def __init__(
        self,
        repository: TrainerRepository,
        my_pokemon_service: MyPokemonService | None = None,
        pokedex_service: PokedexService | None = None,
        trainer_encounter_service: TrainerEncounterService | None = None,
        trainer_party_service: TrainerPartyService | None = None,
        battle_session_service: BattleSessionService | None = None,
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
        if trainer_encounter_service is None:
            from app.domain.trainer.encounter import TrainerEncounterService

            trainer_encounter_service = TrainerEncounterService(
                TrainerEncounterRepository(repository.session),
                trainer_service=self,
            )
        if trainer_party_service is None:
            trainer_party_service = TrainerPartyService(
                TrainerPartyRepository(repository.session),
                trainer_service=self,
            )
        self.my_pokemon_service = my_pokemon_service
        self.pokedex_service = pokedex_service
        self.trainer_encounter_service = trainer_encounter_service
        self.trainer_party_service = trainer_party_service
        self.battle_session_service = battle_session_service or BattleSessionService(
            BattleSessionRepository(repository.session)
        )
        self.home_cache_service = CacheService(
            alias="TrainerHome",
            prefix="trainer",
            logger_params=self.logger_params,
            schema_class=TrainerHomeSchema,
        )
        self.pokemon_center_repository = PokemonCenterRepository(repository.session)

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
            base_capture_rate=capture_rate,
            capture_progress_points=0,
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
                await self.trainer_encounter_service.initialize_for_trainer(
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
                base_capture_rate=trainer.base_capture_rate,
                capture_progress_points=trainer.capture_progress_points,
                created_at=trainer.created_at,
                updated_at=trainer.updated_at,
                deleted_at=trainer.deleted_at,
                my_pokemons=[self.my_pokemon_service.to_schema(created)],
                pokedex=[self.pokedex_service.to_schema(entry) for entry in pokedex],
                known_encounters=[
                    self.trainer_encounter_service.to_encounter_schema(entry)
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

    @staticmethod
    def calculate_effective_capture_rate(
        *,
        base_capture_rate: int,
        capture_progress_points: int,
    ) -> int:
        gain = floor(capture_progress_points / 4) + floor(sqrt(capture_progress_points) * 1.5)
        return min(255, base_capture_rate + gain)

    def apply_capture_progression(
        self,
        *,
        trainer: Trainer,
        progress_points_awarded: int,
    ) -> Trainer:
        trainer.capture_progress_points += progress_points_awarded
        trainer.capture_rate = self.calculate_effective_capture_rate(
            base_capture_rate=trainer.base_capture_rate,
            capture_progress_points=trainer.capture_progress_points,
        )
        return trainer

    async def capture_battle_pokemon(
        self,
        trainer: Trainer,
        payload: CaptureBattlePokemonSchema | None = None,
    ) -> BattleCaptureResultSchema:
        try:
            active_battle = await self.battle_session_service.repository.find_active_by_trainer_id(
                trainer.id
            )
            if active_battle is None:
                latest_battle = await self.battle_session_service.repository.find_latest_by_trainer_id(
                    trainer.id
                )
                if latest_battle is not None and latest_battle.status == BattleSessionStatusEnum.CAPTURED:
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail="Trainer already captured this battle Pokemon",
                    )
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Trainer has no active battle",
                )

            battle_session = active_battle

            if trainer.pokeballs <= 0:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Trainer has no pokeballs left",
                )

            trainer.pokeballs -= 1
            wild_capture_rate = battle_session.wild_pokemon_snapshot.get("capture_rate", 0)

            if trainer.capture_rate < wild_capture_rate:
                result = await self.battle_session_service.create_ineligible_capture_result(
                    entity=battle_session,
                    trainer=trainer,
                )
                await self.repository.session.commit()
                await self.invalidate_home_cache(str(trainer.id))
                return result

            capture_chance = self.battle_session_service.calculate_capture_chance(
                trainer_capture_rate=trainer.capture_rate,
                wild_capture_rate=wild_capture_rate,
                current_hp=battle_session.wild_pokemon_snapshot["current_hp"],
                max_hp=battle_session.wild_pokemon_snapshot["max_hp"],
            )

            if not self.battle_session_service.rolled_capture_success(capture_chance):
                result = await self.battle_session_service.process_capture_failure(
                    entity=battle_session,
                    trainer=trainer,
                    capture_chance=capture_chance,
                )
                await self.repository.session.commit()
                await self.invalidate_home_cache(str(trainer.id))
                return result

            was_discovered = await self.pokedex_service.is_discovered(
                trainer_id=trainer.id,
                pokemon_name=battle_session.wild_pokemon_name,
            )
            my_pokemon = await self.my_pokemon_service.create_owned_for_trainer(
                trainer_id=trainer.id,
                pokemon_name=battle_session.wild_pokemon_name,
                nickname=payload.nickname if payload else None,
                commit=False,
            )
            await self.pokedex_service.discover(
                trainer=trainer,
                pokemon_name=battle_session.wild_pokemon_name,
                commit=False,
            )
            progress_points_awarded = 1 if was_discovered else 2
            self.apply_capture_progression(
                trainer=trainer,
                progress_points_awarded=progress_points_awarded,
            )
            result = await self.battle_session_service.finalize_capture_success(
                entity=battle_session,
                trainer=trainer,
                my_pokemon=self.my_pokemon_service.to_schema(my_pokemon),
                progress_points_awarded=progress_points_awarded,
                capture_chance=capture_chance,
            )
            await self.repository.session.commit()
            await self.invalidate_home_cache(str(trainer.id))
            return result
        except Exception as exception:
            await self.repository.session.rollback()
            handle_service_exception(
                exception,
                logger=logger,
                service="TrainerService",
                operation="capture_battle_pokemon",
                raise_exception=True,
            )


    async def _get_home_encounters(self, trainer: Trainer):
        trainer_encounters = await self.trainer_encounter_service.list_all(trainer_id=str(trainer.id))
        encounters: list[TrainerEncounter] = trainer_encounters if isinstance(trainer_encounters, list) else []
        if not encounters or len(encounters) == 0:
            pokemons = [item.pokemon for item in trainer.my_pokemons]
            all_pokemon_encounters: list[PokemonEncounter] = []
            for pokemon in pokemons:
                if pokemon.encounters:
                    all_pokemon_encounters.extend(pokemon.encounters)
            seen_ids = set()
            unique_encounters: list[PokemonEncounter] = []
            for pokemon_encounter in all_pokemon_encounters:
                encounter_id = pokemon_encounter.id
                if encounter_id not in seen_ids:
                    seen_ids.add(encounter_id)
                    unique_encounters.append(pokemon_encounter)
            return await self.trainer_encounter_service.add_encounters(trainer_id=str(trainer.id), pokemon_encounters=unique_encounters)
        return encounters

    async def get_home(self, trainer: Trainer) -> TrainerHomeSchema:
        key = self._home_key(str(trainer.id))
        cached = await self.home_cache_service.get_one(key)
        if cached:
            return cached
        encounters: list[TrainerEncounter] = await self._get_home_encounters(trainer)

        active_encounter = (
            await self.trainer_encounter_service.get_active_encounter_by_trainer_id(trainer.id)
        )
        trainer_parties = await self.trainer_party_service.list_all(page_filter=FilterPage.build(trainer_id=trainer.id))
        parties: list[TrainerParty] = trainer_parties if isinstance(trainer_parties, list) else []

        active_battle = await self.battle_session_service.get_active_battle_summary_by_trainer_id(
            trainer.id
        )
        latest_discoveries = await self.pokedex_service.list_latest_discoveries(trainer.id)
        latest_healing = await self.pokemon_center_repository.find_latest_by_trainer_id(trainer.id)
        serialized = TrainerHomeSchema(
            party=[
                TrainerPartyMemberSchema.model_validate(party) for party in parties
            ],
            trainer=TrainerSchema.model_validate(trainer),
            encounters=[
                TrainerEncounterSchema.model_validate(encounter) for encounter in encounters
            ],
            active_battle=active_battle,
            active_encounter=active_encounter,
            latest_discoveries = [
                PokedexSchema.model_validate(entry) for entry in latest_discoveries
            ],
            last_healing=(
                LastHealingSummarySchema.model_validate(latest_healing)
                if latest_healing is not None
                else None
            ),
        )
        # await self.home_cache_service.set_one(key, serialized)
        return serialized
