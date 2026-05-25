from __future__ import annotations

import logging
import random
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.manager import CacheManager
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.battle.business import (
    apply_damage,
    build_trainer_party_snapshot,
    build_wild_pokemon_snapshot,
    calculate_capture_chance_percent,
    calculate_damage,
    choose_initial_trainer_pokemon,
    choose_wild_move,
    consume_move_pp,
    ensure_switch_allowed,
    has_remaining_healthy_party,
    resolve_battle_status,
)
from app.domain.trainer.battle.repository import BattleSessionRepository
from app.domain.trainer.battle.schema import (
    ActiveBattleSummarySchema,
    BattleCaptureResultSchema,
    BattleSessionSchema,
    BattleLogSchema,
    BattleSideSchema,
    BattleTurnSchema,
    SwitchBattlePokemonSchema,
    UseBattleMoveSchema,
)
from app.domain.trainer.trainer_party.repository import TrainerPartyRepository
from app.domain.trainer.trainer_party.schema import TrainerPartyMemberSchema
from app.domain.trainer.trainer_party.service import TrainerPartyService
from app.models import (
    BattleLog,
    BattleSession,
    BattleTurn,
    BattleActionTypeEnum,
    BattleActorEnum,
    BattleCaptureOutcomeEnum,
    BattleLogTypeEnum,
    BattleSessionStatusEnum,
    Trainer,
)

logger = logging.getLogger(__name__)


class BattleSessionService(
    BaseService[
        BattleSessionRepository,
        BattleSession,
        BattleSessionSchema,
    ]
):
    def __init__(
        self,
        repository: BattleSessionRepository,
        trainer_party_service: TrainerPartyService | None = None,
        pokemon_service: PokemonService | None = None,
    ) -> None:
        super().__init__(
            alias="BattleSession",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="BattleSessionService",
                operation="battle_session",
            ),
            schema_class=BattleSessionSchema,
            cache_prefix="trainer",
        )
        session = repository.session
        self.trainer_party_service = trainer_party_service
        self.trainer_party_repository = TrainerPartyRepository(session)
        self.pokemon_service = pokemon_service or PokemonService(PokemonRepository(session))
        self.home_cache = CacheManager()

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(BattleSessionRepository(session))

    async def has_active_battle(self, trainer_id: UUID) -> bool:
        return await self.repository.find_active_by_trainer_id(trainer_id) is not None

    async def create_or_resume_battle(
        self,
        *,
        trainer: Trainer,
        exploration_event,
        wild_pokemon,
    ) -> BattleSession:
        active = await self.repository.find_active_by_trainer_id(trainer.id)
        if active is not None:
            return active

        party = await self._get_party_by_trainer_id(trainer.id)
        trainer_party_snapshot = build_trainer_party_snapshot(party)
        active_trainer_pokemon = choose_initial_trainer_pokemon(trainer_party_snapshot)
        wild_detail = await self.pokemon_service.find_detail(wild_pokemon.name)
        wild_snapshot = build_wild_pokemon_snapshot(wild_detail)

        entity = await self.repository.create_session(
            BattleSession(
                trainer_id=trainer.id,
                exploration_event_id=exploration_event.id,
                trainer_active_my_pokemon_id=UUID(active_trainer_pokemon["my_pokemon_id"]),
                wild_pokemon_id=wild_detail.id,
                wild_pokemon_name=wild_detail.name,
                wild_pokemon_level=wild_snapshot["level"],
                status=BattleSessionStatusEnum.ACTIVE,
                trainer_party_snapshot=trainer_party_snapshot,
                wild_pokemon_snapshot=wild_snapshot,
            )
        )
        setattr(entity, "_trainer_context", trainer)
        await self.repository.create_log(
            BattleLog(
                battle_session_id=entity.id,
                log_type=BattleLogTypeEnum.SESSION_STARTED,
                message=f"Wild {wild_detail.name} battle started",
                payload={
                    "exploration_event_id": str(exploration_event.id),
                    "trainer_active_my_pokemon_id": active_trainer_pokemon["my_pokemon_id"],
                },
            )
        )
        return entity

    async def _get_party_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> list[TrainerPartyMemberSchema]:
        if self.trainer_party_service is not None:
            return await self.trainer_party_service.get_party_by_trainer_id(trainer_id)
        entities = await self.trainer_party_repository.list_active_party(trainer_id)
        return [TrainerPartyService.to_party_schema(entity) for entity in entities]

    async def get_active_battle(
        self,
        trainer: Trainer,
    ) -> BattleSessionSchema:
        entity = await self.repository.find_active_by_trainer_id(trainer.id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer has no active battle",
            )
        return self.to_schema(entity)

    async def get_active_battle_summary_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> ActiveBattleSummarySchema | None:
        entity = await self.repository.find_active_by_trainer_id(trainer_id)
        if entity is None:
            return None
        return ActiveBattleSummarySchema(
            battle_session_id=entity.id,
            status=entity.status,
            turn_number=entity.turn_number,
            wild_pokemon_name=entity.wild_pokemon_name,
            wild_pokemon_level=entity.wild_pokemon_level,
            trainer_active_my_pokemon_id=entity.trainer_active_my_pokemon_id,
            has_active_battle=True,
        )

    async def list_logs(
        self,
        trainer: Trainer,
    ) -> list[BattleLogSchema]:
        entity = await self.repository.find_active_by_trainer_id(trainer.id)
        if entity is None:
            entity = await self.repository.find_latest_by_trainer_id(trainer.id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer has no battle session",
            )
        logs = await self.repository.list_logs(entity.id)
        return [BattleLogSchema.model_validate(log) for log in logs]

    async def get_active_entity(
        self,
        trainer_id: UUID,
    ) -> BattleSession:
        return await self._get_active_entity(trainer_id)

    async def create_ineligible_capture_result(
        self,
        *,
        entity: BattleSession,
        trainer: Trainer,
        capture_chance: int | None = None,
    ) -> BattleCaptureResultSchema:
        await self.repository.create_log(
            BattleLog(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                actor=BattleActorEnum.TRAINER,
                log_type=BattleLogTypeEnum.CAPTURE_FAILED,
                message="Capture attempt failed due to insufficient trainer capture rate",
                payload={
                    "reason": BattleCaptureOutcomeEnum.INELIGIBLE_CAPTURE_RATE.value,
                    "trainer_capture_rate": trainer.capture_rate,
                    "wild_capture_rate": entity.wild_pokemon_snapshot.get("capture_rate", 0),
                    "capture_chance": capture_chance,
                },
            )
        )
        return BattleCaptureResultSchema(
            success=False,
            outcome=BattleCaptureOutcomeEnum.INELIGIBLE_CAPTURE_RATE,
            message="Trainer capture rate is too low for this Pokemon",
            battle_session=self.to_schema(entity),
            trainer_pokeballs=trainer.pokeballs,
            trainer_capture_rate=trainer.capture_rate,
            trainer_capture_progress_points=trainer.capture_progress_points,
            progress_points_awarded=0,
            capture_chance=capture_chance,
        )

    async def process_capture_failure(
        self,
        *,
        entity: BattleSession,
        trainer: Trainer,
        capture_chance: int,
    ) -> BattleCaptureResultSchema:
        entity.turn_number += 1
        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.TRAINER,
            action_type=BattleActionTypeEnum.CAPTURE,
            move_name=None,
            message="Trainer used a Pokeball",
            payload={"capture_chance": capture_chance},
            log_type=BattleLogTypeEnum.CAPTURE_ATTEMPT,
        )
        await self.repository.create_log(
            BattleLog(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                actor=BattleActorEnum.TRAINER,
                log_type=BattleLogTypeEnum.CAPTURE_FAILED,
                message="The wild Pokemon broke free",
                payload={
                    "reason": BattleCaptureOutcomeEnum.FAILED_CHANCE.value,
                    "capture_chance": capture_chance,
                },
            )
        )
        await self._process_wild_response(entity)
        return BattleCaptureResultSchema(
            success=False,
            outcome=BattleCaptureOutcomeEnum.FAILED_CHANCE,
            message="The wild Pokemon broke free",
            battle_session=self.to_schema(entity),
            trainer_pokeballs=trainer.pokeballs,
            trainer_capture_rate=trainer.capture_rate,
            trainer_capture_progress_points=trainer.capture_progress_points,
            progress_points_awarded=0,
            capture_chance=capture_chance,
        )

    async def finalize_capture_success(
        self,
        *,
        entity: BattleSession,
        trainer: Trainer,
        my_pokemon,
        progress_points_awarded: int,
        capture_chance: int,
    ) -> BattleCaptureResultSchema:
        entity.turn_number += 1
        entity.status = BattleSessionStatusEnum.CAPTURED
        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.TRAINER,
            action_type=BattleActionTypeEnum.CAPTURE,
            move_name=None,
            message="Trainer used a Pokeball",
            payload={"capture_chance": capture_chance},
            log_type=BattleLogTypeEnum.CAPTURE_ATTEMPT,
        )
        await self.repository.create_log(
            BattleLog(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                actor=BattleActorEnum.TRAINER,
                log_type=BattleLogTypeEnum.CAPTURE_SUCCESS,
                message=f"Trainer captured {entity.wild_pokemon_name}",
                payload={
                    "my_pokemon_id": str(my_pokemon.id),
                    "progress_points_awarded": progress_points_awarded,
                    "capture_chance": capture_chance,
                },
            )
        )
        await self._finalize_battle_if_needed(entity)
        return BattleCaptureResultSchema(
            success=True,
            outcome=BattleCaptureOutcomeEnum.CAPTURED,
            message=f"Trainer captured {entity.wild_pokemon_name}",
            battle_session=self.to_schema(entity),
            my_pokemon=my_pokemon,
            pokedex_updated=True,
            trainer_pokeballs=trainer.pokeballs,
            trainer_capture_rate=trainer.capture_rate,
            trainer_capture_progress_points=trainer.capture_progress_points,
            progress_points_awarded=progress_points_awarded,
            capture_chance=capture_chance,
        )

    @staticmethod
    def calculate_capture_chance(
        *,
        trainer_capture_rate: int,
        wild_capture_rate: int,
        current_hp: int,
        max_hp: int,
    ) -> int:
        return calculate_capture_chance_percent(
            trainer_capture_rate=trainer_capture_rate,
            wild_capture_rate=wild_capture_rate,
            current_hp=current_hp,
            max_hp=max_hp,
        )

    @staticmethod
    def rolled_capture_success(chance_percent: int) -> bool:
        return random.randint(1, 100) <= chance_percent

    async def use_move(
        self,
        trainer: Trainer,
        payload: UseBattleMoveSchema,
    ) -> BattleSessionSchema:
        entity = await self._get_active_entity(trainer.id)
        trainer_member = self._get_active_trainer_member(entity)
        used_move = consume_move_pp(trainer_member["moves"], str(payload.move_id))
        entity.turn_number += 1

        damage = calculate_damage(
            level=trainer_member["level"],
            attack=trainer_member["attack"],
            defense=entity.wild_pokemon_snapshot["defense"],
            power=used_move["power"],
        )
        wild_hp = apply_damage(entity.wild_pokemon_snapshot, damage)

        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.TRAINER,
            action_type=BattleActionTypeEnum.USE_MOVE,
            move_name=used_move["name"],
            message=f"{trainer_member['nickname']} used {used_move['name']}",
            payload={
                "damage": damage,
                "target_hp": wild_hp,
                "move_id": used_move["id"],
            },
        )

        entity.status = resolve_battle_status(
            trainer_member=trainer_member,
            has_remaining_party=has_remaining_healthy_party(entity.trainer_party_snapshot),
            wild_snapshot=entity.wild_pokemon_snapshot,
        )

        if entity.status == BattleSessionStatusEnum.ACTIVE:
            await self._process_wild_response(entity)
        else:
            await self._finalize_battle_if_needed(entity)

        entity.updated_at = None
        await self.repository.session.commit()
        await self._invalidate_home_cache(trainer.id)
        return self.to_schema(entity)

    async def switch_pokemon(
        self,
        trainer: Trainer,
        payload: SwitchBattlePokemonSchema,
    ) -> BattleSessionSchema:
        entity = await self._get_active_entity(trainer.id)
        next_member = ensure_switch_allowed(
            entity.trainer_party_snapshot,
            str(entity.trainer_active_my_pokemon_id) if entity.trainer_active_my_pokemon_id else None,
            str(payload.my_pokemon_id),
        )
        entity.turn_number += 1
        entity.trainer_active_my_pokemon_id = payload.my_pokemon_id
        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.TRAINER,
            action_type=BattleActionTypeEnum.SWITCH,
            move_name=None,
            message=f"Trainer switched to {next_member['nickname']}",
            payload={"my_pokemon_id": next_member["my_pokemon_id"]},
        )
        await self._process_wild_response(entity)
        await self.repository.session.commit()
        await self._invalidate_home_cache(trainer.id)
        return self.to_schema(entity)

    async def flee(
        self,
        trainer: Trainer,
    ) -> BattleSessionSchema:
        entity = await self._get_active_entity(trainer.id)
        entity.turn_number += 1
        entity.status = BattleSessionStatusEnum.ESCAPED
        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.TRAINER,
            action_type=BattleActionTypeEnum.FLEE,
            move_name=None,
            message="Trainer fled from battle",
            payload={},
            log_type=BattleLogTypeEnum.ESCAPED,
        )
        await self._finalize_battle_if_needed(entity)
        await self.repository.session.commit()
        await self._invalidate_home_cache(trainer.id)
        return self.to_schema(entity)

    async def _get_active_entity(
        self,
        trainer_id: UUID,
    ) -> BattleSession:
        entity = await self.repository.find_active_by_trainer_id(trainer_id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer has no active battle",
            )
        return entity

    def _get_active_trainer_member(self, entity: BattleSession) -> dict:
        active_id = str(entity.trainer_active_my_pokemon_id) if entity.trainer_active_my_pokemon_id else None
        for member in entity.trainer_party_snapshot:
            if member["my_pokemon_id"] == active_id:
                return member
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Active trainer Pokemon could not be resolved",
        )

    async def _process_wild_response(
        self,
        entity: BattleSession,
    ) -> None:
        if entity.status != BattleSessionStatusEnum.ACTIVE:
            return

        trainer_member = self._get_active_trainer_member(entity)
        if trainer_member["current_hp"] <= 0:
            entity.status = resolve_battle_status(
                trainer_member=trainer_member,
                has_remaining_party=has_remaining_healthy_party(entity.trainer_party_snapshot),
                wild_snapshot=entity.wild_pokemon_snapshot,
            )
            await self._finalize_battle_if_needed(entity)
            return

        wild_move = choose_wild_move(entity.wild_pokemon_snapshot)
        consume_move_pp(entity.wild_pokemon_snapshot["moves"], wild_move["id"])
        damage = calculate_damage(
            level=entity.wild_pokemon_snapshot["level"],
            attack=entity.wild_pokemon_snapshot["attack"],
            defense=trainer_member["defense"],
            power=wild_move["power"],
        )
        trainer_hp = apply_damage(trainer_member, damage)
        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.WILD,
            action_type=BattleActionTypeEnum.AUTO_RESPONSE,
            move_name=wild_move["name"],
            message=f"Wild {entity.wild_pokemon_name} used {wild_move['name']}",
            payload={
                "damage": damage,
                "target_hp": trainer_hp,
                "move_id": wild_move["id"],
            },
        )
        entity.status = resolve_battle_status(
            trainer_member=trainer_member,
            has_remaining_party=has_remaining_healthy_party(entity.trainer_party_snapshot),
            wild_snapshot=entity.wild_pokemon_snapshot,
        )
        await self._finalize_battle_if_needed(entity)

    async def _record_turn_and_logs(
        self,
        *,
        entity: BattleSession,
        actor: BattleActorEnum,
        action_type: BattleActionTypeEnum,
        move_name: str | None,
        message: str,
        payload: dict,
        log_type: BattleLogTypeEnum = BattleLogTypeEnum.MOVE_USED,
    ) -> None:
        await self.repository.create_turn(
            BattleTurn(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                actor=actor,
                action_type=action_type,
                move_name=move_name,
                payload=payload,
            )
        )
        await self.repository.create_log(
            BattleLog(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                actor=actor,
                log_type=log_type,
                message=message,
                payload=payload,
            )
        )
        if "damage" in payload:
            await self.repository.create_log(
                BattleLog(
                    battle_session_id=entity.id,
                    turn_number=entity.turn_number,
                    actor=actor,
                    log_type=BattleLogTypeEnum.DAMAGE_DEALT,
                    message=f"{payload['damage']} damage dealt",
                    payload=payload,
                )
            )

    async def _finalize_battle_if_needed(
        self,
        entity: BattleSession,
    ) -> None:
        if entity.status == BattleSessionStatusEnum.ACTIVE:
            return
        message_by_status = {
            BattleSessionStatusEnum.WILD_POKEMON_DEFEATED: "Trainer defeated the wild Pokemon",
            BattleSessionStatusEnum.TRAINER_DEFEATED: "Trainer was defeated in battle",
            BattleSessionStatusEnum.ESCAPED: "Trainer fled from battle",
            BattleSessionStatusEnum.CAPTURED: "Trainer captured the wild Pokemon",
        }
        await self.repository.create_log(
            BattleLog(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                log_type=BattleLogTypeEnum.SESSION_FINISHED,
                message=message_by_status[entity.status],
                payload={"status": entity.status.value},
            )
        )

    async def _invalidate_home_cache(self, trainer_id: UUID) -> None:
        key = self.home_cache.build_key("trainer", "home", str(trainer_id))
        await self.home_cache.delete_cache(key)

    @staticmethod
    def _build_side_schema(snapshot: dict) -> BattleSideSchema:
        return BattleSideSchema(
            my_pokemon_id=UUID(snapshot["my_pokemon_id"]) if snapshot.get("my_pokemon_id") else None,
            pokemon_id=UUID(snapshot["pokemon_id"]) if snapshot.get("pokemon_id") else None,
            name=snapshot["name"],
            nickname=snapshot.get("nickname"),
            level=snapshot["level"],
            current_hp=snapshot["current_hp"],
            max_hp=snapshot["max_hp"],
            attack=snapshot["attack"],
            defense=snapshot["defense"],
            special_attack=snapshot["special_attack"],
            special_defense=snapshot["special_defense"],
            speed=snapshot["speed"],
            moves=snapshot.get("moves", []),
        )

    def to_schema(self, entity: BattleSession) -> BattleSessionSchema:
        trainer_member = self._get_active_trainer_member(entity)
        trainer_context = getattr(entity, "trainer", None) or getattr(entity, "_trainer_context", None)
        party = [self._build_side_schema(member) for member in entity.trainer_party_snapshot]
        return BattleSessionSchema(
            id=entity.id,
            trainer_id=entity.trainer_id,
            exploration_event_id=entity.exploration_event_id,
            trainer_active_my_pokemon_id=entity.trainer_active_my_pokemon_id,
            wild_pokemon_id=entity.wild_pokemon_id,
            wild_pokemon_name=entity.wild_pokemon_name,
            wild_pokemon_level=entity.wild_pokemon_level,
            turn_number=entity.turn_number,
            status=entity.status,
            trainer_pokeballs=trainer_context.pokeballs if trainer_context else 0,
            trainer_capture_rate=trainer_context.capture_rate if trainer_context else 0,
            trainer_side=self._build_side_schema(trainer_member),
            wild_side=self._build_side_schema(entity.wild_pokemon_snapshot),
            party=party,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def to_turn_schema(entity: BattleTurn) -> BattleTurnSchema:
        return BattleTurnSchema.model_validate(entity)
