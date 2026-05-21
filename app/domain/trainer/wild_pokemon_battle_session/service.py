from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.trainer_party.repository import TrainerPartyRepository
from app.domain.trainer.trainer_party.schema import TrainerPartyMemberSchema
from app.domain.trainer.trainer_party.service import TrainerPartyService
from app.domain.trainer.wild_pokemon_battle_session.business import (
    apply_damage,
    build_trainer_party_snapshot,
    build_wild_pokemon_snapshot,
    calculate_damage,
    choose_initial_trainer_pokemon,
    choose_wild_move,
    consume_move_pp,
    ensure_switch_allowed,
    has_remaining_healthy_party,
    resolve_battle_status,
)
from app.domain.trainer.wild_pokemon_battle_session.repository import (
    WildPokemonBattleSessionRepository,
)
from app.domain.trainer.wild_pokemon_battle_session.schema import (
    BattleLogSchema,
    BattleSideSchema,
    BattleTurnSchema,
    SwitchBattlePokemonSchema,
    UseBattleMoveSchema,
    WildPokemonBattleSessionSchema,
)
from app.models import (
    BattleActionTypeEnum,
    BattleActorEnum,
    BattleLogTypeEnum,
    BattleSessionStatusEnum,
    Trainer,
    WildPokemonBattleLog,
    WildPokemonBattleSession,
    WildPokemonBattleTurn,
)

logger = logging.getLogger(__name__)


class WildPokemonBattleSessionService(
    BaseService[
        WildPokemonBattleSessionRepository,
        WildPokemonBattleSession,
        WildPokemonBattleSessionSchema,
    ]
):
    def __init__(
        self,
        repository: WildPokemonBattleSessionRepository,
        trainer_party_service: TrainerPartyService | None = None,
        pokemon_service: PokemonService | None = None,
    ) -> None:
        super().__init__(
            alias="WildPokemonBattleSession",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="WildPokemonBattleSessionService",
                operation="wild_pokemon_battle_session",
            ),
            schema_class=WildPokemonBattleSessionSchema,
            cache_prefix="trainer",
        )
        session = repository.session
        self.trainer_party_service = trainer_party_service
        self.trainer_party_repository = TrainerPartyRepository(session)
        self.pokemon_service = pokemon_service or PokemonService(PokemonRepository(session))

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(WildPokemonBattleSessionRepository(session))

    async def has_active_battle(self, trainer_id: UUID) -> bool:
        return await self.repository.find_active_by_trainer_id(trainer_id) is not None

    async def create_or_resume_battle(
        self,
        *,
        trainer: Trainer,
        exploration_event,
        wild_pokemon,
    ) -> WildPokemonBattleSession:
        active = await self.repository.find_active_by_trainer_id(trainer.id)
        if active is not None:
            return active

        party = await self._get_party_by_trainer_id(trainer.id)
        trainer_party_snapshot = build_trainer_party_snapshot(party)
        active_trainer_pokemon = choose_initial_trainer_pokemon(trainer_party_snapshot)
        wild_detail = await self.pokemon_service.find_detail(wild_pokemon.name)
        wild_snapshot = build_wild_pokemon_snapshot(wild_detail)

        entity = await self.repository.create_session(
            WildPokemonBattleSession(
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
        await self.repository.create_log(
            WildPokemonBattleLog(
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
    ) -> WildPokemonBattleSessionSchema:
        entity = await self.repository.find_active_by_trainer_id(trainer.id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer has no active battle",
            )
        return self.to_schema(entity)

    async def list_logs(
        self,
        trainer: Trainer,
    ) -> list[BattleLogSchema]:
        entity = await self.repository.find_active_by_trainer_id(trainer.id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer has no active battle",
            )
        logs = await self.repository.list_logs(entity.id)
        return [BattleLogSchema.model_validate(log) for log in logs]

    async def use_move(
        self,
        trainer: Trainer,
        payload: UseBattleMoveSchema,
    ) -> WildPokemonBattleSessionSchema:
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
        return self.to_schema(entity)

    async def switch_pokemon(
        self,
        trainer: Trainer,
        payload: SwitchBattlePokemonSchema,
    ) -> WildPokemonBattleSessionSchema:
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
        return self.to_schema(entity)

    async def flee(
        self,
        trainer: Trainer,
    ) -> WildPokemonBattleSessionSchema:
        entity = await self._get_active_entity(trainer.id)
        entity.turn_number += 1
        entity.status = BattleSessionStatusEnum.FLED
        await self._record_turn_and_logs(
            entity=entity,
            actor=BattleActorEnum.TRAINER,
            action_type=BattleActionTypeEnum.FLEE,
            move_name=None,
            message="Trainer fled from battle",
            payload={},
            log_type=BattleLogTypeEnum.FLED,
        )
        await self._finalize_battle_if_needed(entity)
        await self.repository.session.commit()
        return self.to_schema(entity)

    async def _get_active_entity(
        self,
        trainer_id: UUID,
    ) -> WildPokemonBattleSession:
        entity = await self.repository.find_active_by_trainer_id(trainer_id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer has no active battle",
            )
        return entity

    def _get_active_trainer_member(self, entity: WildPokemonBattleSession) -> dict:
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
        entity: WildPokemonBattleSession,
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
        entity: WildPokemonBattleSession,
        actor: BattleActorEnum,
        action_type: BattleActionTypeEnum,
        move_name: str | None,
        message: str,
        payload: dict,
        log_type: BattleLogTypeEnum = BattleLogTypeEnum.MOVE_USED,
    ) -> None:
        await self.repository.create_turn(
            WildPokemonBattleTurn(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                actor=actor,
                action_type=action_type,
                move_name=move_name,
                payload=payload,
            )
        )
        await self.repository.create_log(
            WildPokemonBattleLog(
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
                WildPokemonBattleLog(
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
        entity: WildPokemonBattleSession,
    ) -> None:
        if entity.status == BattleSessionStatusEnum.ACTIVE:
            return
        message_by_status = {
            BattleSessionStatusEnum.WON: "Trainer won the battle",
            BattleSessionStatusEnum.LOST: "Trainer lost the battle",
            BattleSessionStatusEnum.FLED: "Trainer fled from battle",
        }
        await self.repository.create_log(
            WildPokemonBattleLog(
                battle_session_id=entity.id,
                turn_number=entity.turn_number,
                log_type=BattleLogTypeEnum.SESSION_FINISHED,
                message=message_by_status[entity.status],
                payload={"status": entity.status.value},
            )
        )

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

    def to_schema(self, entity: WildPokemonBattleSession) -> WildPokemonBattleSessionSchema:
        trainer_member = self._get_active_trainer_member(entity)
        party = [self._build_side_schema(member) for member in entity.trainer_party_snapshot]
        return WildPokemonBattleSessionSchema(
            id=entity.id,
            trainer_id=entity.trainer_id,
            exploration_event_id=entity.exploration_event_id,
            trainer_active_my_pokemon_id=entity.trainer_active_my_pokemon_id,
            wild_pokemon_id=entity.wild_pokemon_id,
            wild_pokemon_name=entity.wild_pokemon_name,
            wild_pokemon_level=entity.wild_pokemon_level,
            turn_number=entity.turn_number,
            status=entity.status,
            trainer_side=self._build_side_schema(trainer_member),
            wild_side=self._build_side_schema(entity.wild_pokemon_snapshot),
            party=party,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def to_turn_schema(entity: WildPokemonBattleTurn) -> BattleTurnSchema:
        return BattleTurnSchema.model_validate(entity)
