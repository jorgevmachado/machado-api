import random

from app.domain.trainer.battle.schema import BattleProcessedSchema, OpponentDamageSchema
from app.domain.trainer.progression import (
    calculate_progression,
    AttributesCalculatedSchema,
)
from app.models import OwnedPokemonMove, TrainerParty, PokedexEntry, OwnedPokemon, Move
from app.models.enums import BattleSessionStatusEnum


def build_trainer_party_snapshot(party: TrainerParty) -> dict:
    owned_pokemon = party.owned_pokemon
    return {
        "id": str(party.id),
        "hp": owned_pokemon.hp,
        "slot": party.slot,
        "name": owned_pokemon.name,
        "moves": [build_snapshot_move(move) for move in owned_pokemon.moves],
        "level": owned_pokemon.level,
        "speed": owned_pokemon.speed,
        "max_hp": owned_pokemon.max_hp,
        "attack": owned_pokemon.attack,
        "defense": owned_pokemon.defense,
        "nickname": owned_pokemon.nickname,
        "experience": owned_pokemon.experience,
        "is_active": party.is_active,
        "pokemon_id": str(owned_pokemon.pokemon_id),
        "capture_rate": owned_pokemon.pokemon.capture_rate,
        "special_attack": owned_pokemon.special_attack,
        "special_defense": owned_pokemon.special_defense,
        "owned_pokemon_id": str(owned_pokemon.id),
    }


def build_snapshot_move(move: OwnedPokemonMove) -> dict:
    return {
        "id": str(move.id),
        "pp": move.pp,
        "name": move.pokemon_move.name,
        "type": move.pokemon_move.type,
        "power": move.pokemon_move.power,
        "max_pp": move.max_pp,
        "accuracy": move.pokemon_move.accuracy,
        "pokemon_move_id": str(move.pokemon_move_id),
    }


def build_wild_pokemon_snapshot(wild_pokemon: PokedexEntry) -> dict:
    return {
        "id": str(wild_pokemon.id),
        "hp": wild_pokemon.hp,
        "slot": 0,
        "name": wild_pokemon.pokemon.name,
        "moves": [
            {
                "id": str(move.id),
                "pp": move.pp,
                "name": move.name,
                "type": move.type,
                "power": move.power,
                "max_pp": move.pp,
                "accuracy": move.accuracy,
                "pokemon_move_id": str(move.id),
            }
            for move in wild_pokemon.pokemon.moves[:4]
        ],
        "level": wild_pokemon.level,
        "speed": wild_pokemon.speed,
        "max_hp": wild_pokemon.hp,
        "attack": wild_pokemon.attack,
        "defense": wild_pokemon.defense,
        "nickname": wild_pokemon.pokemon.name,
        "is_active": True,
        "experience": wild_pokemon.experience,
        "pokemon_id": str(wild_pokemon.pokemon_id),
        "capture_rate": wild_pokemon.pokemon.capture_rate,
        "special_attack": wild_pokemon.special_attack,
        "special_defense": wild_pokemon.special_defense,
    }


def process_battle(
    move: Move,
    status: BattleSessionStatusEnum,
    wild_pokemon: PokedexEntry,
    trainer_party: TrainerParty,
) -> BattleProcessedSchema:
    owned_pokemon = trainer_party.owned_pokemon
    battle_processed = BattleProcessedSchema(
        error=False,
        status=status,
        wild_pokemon_damage=0,
        wild_pokemon_missed=False,
        owned_pokemon_damage=0,
        owned_pokemon_missed=False,
        wild_pokemon_fainted=False,
        owned_pokemon_fainted=False,
        wild_pokemon_progression=AttributesCalculatedSchema(
            hp=wild_pokemon.hp,
            level=wild_pokemon.level,
            speed=wild_pokemon.speed,
            attack=wild_pokemon.attack,
            max_hp=wild_pokemon.max_hp,
            defense=wild_pokemon.defense,
            level_up=False,
            experience=wild_pokemon.experience,
            special_attack=wild_pokemon.special_attack,
            special_defense=wild_pokemon.special_defense,
        ),
        owned_pokemon_progression=AttributesCalculatedSchema(
            hp=owned_pokemon.hp,
            level=owned_pokemon.level,
            speed=owned_pokemon.speed,
            attack=owned_pokemon.attack,
            max_hp=owned_pokemon.max_hp,
            defense=owned_pokemon.defense,
            level_up=False,
            experience=owned_pokemon.experience,
            special_attack=owned_pokemon.special_attack,
            special_defense=owned_pokemon.special_defense,
        ),
        owned_pokemon_move_name=move.name,
    )

    result_wild_damage = _calculate_opponent_damage(
        level=owned_pokemon.level,
        attack=owned_pokemon.attack,
        opponent_hp=wild_pokemon.hp,
        opponent_defense=wild_pokemon.defense,
        move=move,
    )

    if result_wild_damage is None:
        battle_processed.error = True
        battle_processed.error_message = (
            f"Owned Pokemon {owned_pokemon.name} has no move with id {move.id}"
        )
        return battle_processed

    battle_processed.wild_pokemon_damage = result_wild_damage.damage
    battle_processed.owned_pokemon_missed = result_wild_damage.missed

    current_wild_pokemon_hp = result_wild_damage.current_hp
    current_trainer_pokemon_hp = owned_pokemon.hp
    battle_processed.wild_pokemon_fainted = current_wild_pokemon_hp <= 0
    if not battle_processed.wild_pokemon_fainted:
        wild_pokemon_move = random.sample(wild_pokemon.pokemon.moves, 1)[0]
        battle_processed.wild_pokemon_move_name = (
            wild_pokemon_move.name if wild_pokemon else None
        )
        result_trainer_pokemon_damage = _calculate_opponent_damage(
            level=wild_pokemon.level,
            attack=wild_pokemon.attack,
            opponent_hp=owned_pokemon.hp,
            opponent_defense=owned_pokemon.defense,
            move=wild_pokemon_move,
        )
        current_trainer_pokemon_hp = (
            result_trainer_pokemon_damage.current_hp
            if result_trainer_pokemon_damage
            else None
        )
        battle_processed.owned_pokemon_damage = (
            result_trainer_pokemon_damage.damage if result_trainer_pokemon_damage else 0
        )
        battle_processed.wild_pokemon_missed = (
            result_trainer_pokemon_damage.missed
            if result_trainer_pokemon_damage
            else False
        )

    if current_trainer_pokemon_hp is None:
        battle_processed.error = True
        battle_processed.error_message = f"Wild Pokemon {wild_pokemon.name} has no move"
        return battle_processed

    battle_processed.owned_pokemon_fainted = current_trainer_pokemon_hp <= 0
    battle_processed.status = _resolve_battle_session_status(
        owned_pokemon_missed=battle_processed.owned_pokemon_missed,
        wild_pokemon_fainted=battle_processed.wild_pokemon_fainted,
        owned_pokemon_fainted=battle_processed.owned_pokemon_fainted,
    )
    owned_pokemon_progression = calculate_progression(
        hp=current_trainer_pokemon_hp,
        level=owned_pokemon.level,
        speed=owned_pokemon.speed,
        attack=owned_pokemon.attack,
        max_hp=owned_pokemon.max_hp,
        defense=owned_pokemon.defense,
        experience=owned_pokemon.experience,
        special_attack=owned_pokemon.special_attack,
        special_defense=owned_pokemon.special_defense,
        opponent_level=wild_pokemon.level,
        opponent_fainted=battle_processed.wild_pokemon_fainted,
        opponent_base_experience=wild_pokemon.pokemon.base_experience or 0,
        growth_rate=owned_pokemon.pokemon.growth_rate,
    )
    if not owned_pokemon_progression:
        battle_processed.error = True
        battle_processed.error_message = (
            f"Owned Pokemon {owned_pokemon.name} has no Growth Rate"
        )
        return battle_processed

    battle_processed.owned_pokemon_progression = owned_pokemon_progression

    wild_pokemon_progression = calculate_progression(
        hp=current_wild_pokemon_hp,
        level=wild_pokemon.level,
        speed=wild_pokemon.speed,
        attack=wild_pokemon.attack,
        max_hp=wild_pokemon.max_hp,
        defense=wild_pokemon.defense,
        experience=wild_pokemon.experience,
        special_attack=wild_pokemon.special_attack,
        special_defense=wild_pokemon.special_defense,
        opponent_level=owned_pokemon.level,
        opponent_fainted=current_trainer_pokemon_hp <= 0,
        opponent_base_experience=owned_pokemon.pokemon.base_experience or 0,
        growth_rate=wild_pokemon.pokemon.growth_rate,
    )

    if not wild_pokemon_progression:
        battle_processed.error = True
        battle_processed.error_message = (
            f"Wild Pokemon {wild_pokemon.name} has no Growth Rate"
        )
        return battle_processed

    battle_processed.wild_pokemon_progression = wild_pokemon_progression
    return battle_processed


def build_payload(
    wild_pokemon: PokedexEntry,
    trainer_active_pokemon: OwnedPokemon,
    message: str | None = None,
    battle_result: BattleProcessedSchema | None = None,
) -> dict:
    error = battle_result.error if battle_result else False
    trainer_active_pokemon_move_name = (
        battle_result.owned_pokemon_move_name if battle_result else None
    )
    wild_pokemon_move_name = (
        battle_result.wild_pokemon_move_name if battle_result else None
    )
    payload_message = build_payload_message(
        error=error,
        status=battle_result.status if battle_result else None,
        message=message,
        error_message=battle_result.error_message if battle_result else None,
    )
    payload: dict = {
        "error": error,
        "message": payload_message,
        "wild_pokemon_id": str(wild_pokemon.id),
        "wild_pokemon_name": wild_pokemon.name,
        "trainer_active_pokemon_id": str(trainer_active_pokemon.id),
        "trainer_active_pokemon_name": trainer_active_pokemon.name,
        "wild_pokemon_damage": battle_result.wild_pokemon_damage
        if battle_result
        else 0,
        "wild_pokemon_missed": battle_result.wild_pokemon_missed
        if battle_result
        else False,
        "wild_pokemon_fainted": battle_result.wild_pokemon_fainted
        if battle_result
        else False,
        "wild_pokemon_level_up": battle_result.wild_pokemon_progression.level_up
        if battle_result
        else False,
        "trainer_active_pokemon_damage": battle_result.owned_pokemon_damage
        if battle_result
        else 0,
        "trainer_active_pokemon_missed": battle_result.owned_pokemon_missed
        if battle_result
        else False,
        "trainer_active_pokemon_fainted": battle_result.owned_pokemon_fainted
        if battle_result
        else False,
        "trainer_active_pokemon_level_up": battle_result.owned_pokemon_progression.level_up
        if battle_result
        else False,
    }
    if trainer_active_pokemon_move_name is not None:
        payload["trainer_active_pokemon_move_name"] = trainer_active_pokemon_move_name
    if wild_pokemon_move_name is not None:
        payload["wild_pokemon_move_name"] = wild_pokemon_move_name

    return payload


def build_payload_message(
    error: bool = False,
    message: str | None = None,
    error_message: str | None = None,
    status: BattleSessionStatusEnum | None = None,
) -> str:
    fallback_message = "An error occurred during the battle"
    if message:
        return message
    if error:
        status = None
    if status == BattleSessionStatusEnum.ACTIVE:
        return "Battle in progress"
    if status == BattleSessionStatusEnum.TRAINER_DEFEATED:
        return "Trainer defeated"
    if status == BattleSessionStatusEnum.WILD_POKEMON_DEFEATED:
        return "Wild Pokemon defeated"
    if status == BattleSessionStatusEnum.ESCAPED:
        return "Trainer escaped"
    return error_message or fallback_message


def _resolve_battle_session_status(
    owned_pokemon_missed: bool,
    wild_pokemon_fainted: bool,
    owned_pokemon_fainted: bool,
) -> BattleSessionStatusEnum:

    if wild_pokemon_fainted:
        return BattleSessionStatusEnum.WILD_POKEMON_DEFEATED

    if owned_pokemon_fainted:
        return BattleSessionStatusEnum.TRAINER_DEFEATED

    if owned_pokemon_missed:
        return BattleSessionStatusEnum.ESCAPED

    return BattleSessionStatusEnum.ACTIVE


def _calculate_opponent_damage(
    level: int,
    attack: int,
    opponent_hp: int,
    opponent_defense: int,
    move: Move | None,
) -> OpponentDamageSchema | None:
    if not move:
        return None

    result = OpponentDamageSchema(
        damage=0,
        missed=_missed(move.accuracy),
        current_hp=opponent_hp,
    )

    if result.missed:
        return result

    damage = _calculate_damage(
        level=level,
        attack=attack,
        defense=opponent_defense,
        power=move.power,
    )
    current_hp = _apply_damage(
        hp=opponent_hp,
        damage=damage,
    )
    result.damage = damage
    result.current_hp = current_hp
    return result


def _missed(accuracy: int) -> bool:
    if accuracy <= 0:
        return True
    hot_roll = random.randint(1, 100)
    return hot_roll > accuracy


def _calculate_damage(level: int, attack: int, defense: int, power: int) -> int:
    safe_power = power if power > 0 else 1
    safe_attack = attack if attack > 0 else 1
    safe_defense = defense if defense > 0 else 1
    raw = safe_power + level + (safe_attack // 2) - (safe_defense // 4)
    return max(1, raw)


def _apply_damage(hp: int, damage: int) -> int:
    return max(0, hp - damage)
