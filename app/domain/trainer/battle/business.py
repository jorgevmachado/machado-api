from __future__ import annotations

from http import HTTPStatus

from fastapi import HTTPException

from app.domain.trainer.trainer_party.schema import TrainerPartyMemberSchema
from app.models.enums import BattleSessionStatusEnum


def build_snapshot_move(move) -> dict:
    return {
        "id": str(move.id),
        "pokemon_move_id": str(move.pokemon_move_id),
        "name": move.pokemon_move_name,
        "type": move.pokemon_move_type,
        "power": move.pokemon_move_power,
        "accuracy": move.pokemon_move_accuracy,
        "pp": move.pp,
        "max_pp": move.max_pp,
    }


def build_trainer_party_snapshot(
    party: list[TrainerPartyMemberSchema],
) -> list[dict]:
    snapshot: list[dict] = []
    for member in party:
        pokemon = member.my_pokemon
        snapshot.append(
            {
                "slot": member.slot,
                "is_active": member.is_active,
                "my_pokemon_id": str(pokemon.id),
                "name": pokemon.name,
                "nickname": pokemon.nickname,
                "level": pokemon.level,
                "current_hp": pokemon.hp,
                "max_hp": pokemon.max_hp,
                "attack": pokemon.attack,
                "defense": pokemon.defense,
                "special_attack": pokemon.special_attack,
                "special_defense": pokemon.special_defense,
                "speed": pokemon.speed,
                "moves": [build_snapshot_move(move) for move in pokemon.moves],
            }
        )
    return snapshot


def build_wild_pokemon_snapshot(pokemon) -> dict:
    return {
        "pokemon_id": str(pokemon.id),
        "name": pokemon.name,
        "level": 1,
        "current_hp": pokemon.hp or 1,
        "max_hp": pokemon.hp or 1,
        "attack": pokemon.attack or 1,
        "defense": pokemon.defense or 1,
        "special_attack": pokemon.special_attack or 1,
        "special_defense": pokemon.special_defense or 1,
        "speed": pokemon.speed or 1,
        "moves": [
            {
                "id": str(move.id),
                "name": move.name,
                "type": move.type,
                "power": move.power,
                "accuracy": move.accuracy,
                "pp": move.pp,
                "max_pp": move.pp,
            }
            for move in pokemon.moves[:4]
        ],
    }


def choose_initial_trainer_pokemon(party_snapshot: list[dict]) -> dict:
    if not party_snapshot:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Trainer has no active party for battle",
        )
    for member in party_snapshot:
        if member["current_hp"] > 0:
            return member
    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail="Trainer has no battle-ready Pokemon",
    )


def get_party_member_or_404(party_snapshot: list[dict], my_pokemon_id: str) -> dict:
    for member in party_snapshot:
        if member["my_pokemon_id"] == my_pokemon_id:
            return member
    raise HTTPException(
        status_code=HTTPStatus.NOT_FOUND,
        detail="Trainer Pokemon not found in active battle party",
    )


def ensure_switch_allowed(
    party_snapshot: list[dict],
    active_my_pokemon_id: str | None,
    next_my_pokemon_id: str,
) -> dict:
    next_member = get_party_member_or_404(party_snapshot, next_my_pokemon_id)
    if next_member["current_hp"] <= 0:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Trainer cannot switch to a fainted Pokemon",
        )
    if next_member["my_pokemon_id"] == active_my_pokemon_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Trainer Pokemon is already active",
        )
    return next_member


def choose_wild_move(wild_snapshot: dict) -> dict:
    for move in wild_snapshot.get("moves", []):
        if move["pp"] > 0:
            return move
    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail="Wild Pokemon has no moves with PP left",
    )


def consume_move_pp(moves: list[dict], move_id: str) -> dict:
    for move in moves:
        if move["id"] == move_id:
            if move["pp"] <= 0:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Selected move has no PP left",
                )
            move["pp"] -= 1
            return move
    raise HTTPException(
        status_code=HTTPStatus.NOT_FOUND,
        detail="Selected move is not available",
    )


def calculate_damage(*, level: int, attack: int, defense: int, power: int) -> int:
    safe_power = power if power > 0 else 1
    safe_attack = attack if attack > 0 else 1
    safe_defense = defense if defense > 0 else 1
    raw = safe_power + level + (safe_attack // 2) - (safe_defense // 4)
    return max(1, raw)


def apply_damage(snapshot: dict, damage: int) -> int:
    current_hp = snapshot["current_hp"]
    next_hp = max(0, current_hp - damage)
    snapshot["current_hp"] = next_hp
    return next_hp


def resolve_battle_status(
    *,
    trainer_member: dict,
    has_remaining_party: bool,
    wild_snapshot: dict,
) -> BattleSessionStatusEnum:
    if wild_snapshot["current_hp"] <= 0:
        return BattleSessionStatusEnum.WILD_POKEMON_DEFEATED
    if trainer_member["current_hp"] <= 0 and not has_remaining_party:
        return BattleSessionStatusEnum.TRAINER_DEFEATED
    return BattleSessionStatusEnum.ACTIVE


def has_remaining_healthy_party(party_snapshot: list[dict]) -> bool:
    for member in party_snapshot:
        if member["current_hp"] > 0:
            return True
    return False
