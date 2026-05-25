from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.battle.business import (
    build_snapshot_move,
    build_wild_pokemon_snapshot,
    calculate_damage,
    choose_initial_trainer_pokemon,
    choose_wild_move,
    consume_move_pp,
    ensure_switch_allowed,
    get_party_member_or_404,
    has_remaining_healthy_party,
    resolve_battle_status,
)
from app.models.enums import BattleSessionStatusEnum


def test_build_snapshot_move_and_wild_snapshot_cover_serializers():
    move = SimpleNamespace(
        id=uuid4(),
        pokemon_move_id=uuid4(),
        pokemon_move_name='tackle',
        pokemon_move_type='normal',
        pokemon_move_power=8,
        pokemon_move_accuracy=100,
        pp=10,
        max_pp=10,
    )
    wild_move = SimpleNamespace(
        id=uuid4(),
        name='scratch',
        type='normal',
        power=5,
        accuracy=100,
        pp=15,
    )

    result = build_snapshot_move(move)
    wild = build_wild_pokemon_snapshot(
        SimpleNamespace(
            id=uuid4(),
            name='pikachu',
            capture_rate=120,
            hp=12,
            attack=11,
            defense=8,
            special_attack=10,
            special_defense=8,
            speed=11,
            moves=[wild_move],
        )
    )

    assert result['name'] == 'tackle'
    assert wild['moves'][0]['name'] == 'scratch'


def test_choose_initial_trainer_pokemon_raises_without_available_party():
    with pytest.raises(HTTPException) as exc_info:
        choose_initial_trainer_pokemon([])

    assert exc_info.value.status_code == 400


def test_choose_initial_trainer_pokemon_raises_without_healthy_member():
    with pytest.raises(HTTPException) as exc_info:
        choose_initial_trainer_pokemon([{'current_hp': 0}])

    assert exc_info.value.status_code == 400


def test_get_party_member_or_404_and_switch_rules_cover_missing_and_fainted():
    party = [
        {'my_pokemon_id': 'one', 'current_hp': 0, 'nickname': 'One'},
        {'my_pokemon_id': 'two', 'current_hp': 5, 'nickname': 'Two'},
    ]

    with pytest.raises(HTTPException) as missing_exc:
        get_party_member_or_404(party, 'missing')
    assert missing_exc.value.status_code == 404

    with pytest.raises(HTTPException) as fainted_exc:
        ensure_switch_allowed(party, 'two', 'one')
    assert fainted_exc.value.status_code == 400

    assert ensure_switch_allowed(party, 'one', 'two')['nickname'] == 'Two'


def test_choose_wild_move_raises_when_no_pp_is_available():
    with pytest.raises(HTTPException) as exc_info:
        choose_wild_move({'moves': [{'pp': 0}]})

    assert exc_info.value.status_code == 400


def test_consume_move_pp_raises_when_move_is_missing():
    with pytest.raises(HTTPException) as exc_info:
        consume_move_pp([{'id': 'one', 'pp': 1}], 'two')

    assert exc_info.value.status_code == 404


def test_calculate_damage_and_party_health_cover_edge_branches():
    assert calculate_damage(level=1, attack=0, defense=0, power=0) == 2
    assert has_remaining_healthy_party([{'current_hp': 0}]) is False


def test_resolve_battle_status_returns_trainer_defeated_when_trainer_has_no_remaining_party():
    result = resolve_battle_status(
        trainer_member={'current_hp': 0},
        has_remaining_party=False,
        wild_snapshot={'current_hp': 5},
    )

    assert result == BattleSessionStatusEnum.TRAINER_DEFEATED
