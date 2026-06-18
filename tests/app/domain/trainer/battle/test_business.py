from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.domain.trainer.battle.business import (
    _apply_damage,
    _calculate_damage,
    _calculate_opponent_damage,
    _missed,
    _resolve_battle_session_status,
    build_payload,
    build_snapshot_move,
    build_trainer_party_snapshot,
    build_wild_pokemon_snapshot,
    process_battle,
)
from app.domain.trainer.battle.schema import OpponentDamageSchema
from app.domain.trainer.progression import AttributesCalculatedSchema
from app.models.enums import BattleSessionStatusEnum


def _make_move():
    return SimpleNamespace(
        id=uuid4(),
        pp=15,
        max_pp=15,
        pokemon_move_id=uuid4(),
        pokemon_move=SimpleNamespace(
            type="fire",
            name="ember",
            power=40,
            accuracy=100,
        ),
    )


def _make_party(moves=None):
    owned = SimpleNamespace(
        id=uuid4(),
        name="charmander",
        hp=49,
        max_hp=49,
        attack=52,
        defense=43,
        speed=65,
        level=5,
        experience=1,
        special_attack=60,
        special_defense=50,
        nickname="char",
        pokemon_id=uuid4(),
        pokemon=SimpleNamespace(capture_rate=5),
        moves=moves or [],
    )
    return SimpleNamespace(id=uuid4(), slot=1, is_active=True, owned_pokemon=owned)


def _make_wild_pokemon(moves=None):
    pokemon = SimpleNamespace(
        id=uuid4(),
        name="pidgey",
        capture_rate=255,
        moves=moves or [],
    )
    return SimpleNamespace(
        id=uuid4(),
        pokemon_id=uuid4(),
        hp=40,
        max_hp=40,
        attack=45,
        defense=40,
        experience=40,
        speed=56,
        level=5,
        special_attack=35,
        special_defense=35,
        pokemon=pokemon,
    )


# ── build_snapshot_move ──────────────────────────────────────────────────────


def test_build_snapshot_move_returns_expected_dict():
    move = _make_move()
    result = build_snapshot_move(move)

    assert result["id"] == str(move.id)
    assert result["pp"] == move.pp
    assert result["max_pp"] == move.max_pp
    assert result["type"] == move.pokemon_move.type
    assert result["name"] == move.pokemon_move.name
    assert result["power"] == move.pokemon_move.power
    assert result["accuracy"] == move.pokemon_move.accuracy
    assert result["pokemon_move_id"] == str(move.pokemon_move_id)


# ── build_trainer_party_snapshot ─────────────────────────────────────────────


def test_build_trainer_party_snapshot_returns_one_entry():
    move = _make_move()
    party = _make_party(moves=[move])
    entry = build_trainer_party_snapshot(party)

    owned = party.owned_pokemon
    assert entry["id"] == str(party.id)
    assert entry["hp"] == owned.hp
    assert entry["slot"] == party.slot
    assert entry["name"] == owned.name
    assert entry["speed"] == owned.speed
    assert entry["level"] == owned.level
    assert entry["max_hp"] == owned.max_hp
    assert entry["attack"] == owned.attack
    assert entry["defense"] == owned.defense
    assert entry["nickname"] == owned.nickname
    assert entry["is_active"] == party.is_active
    assert entry["experience"] == owned.experience
    assert entry["capture_rate"] == owned.pokemon.capture_rate
    assert entry["pokemon_id"] == str(owned.pokemon_id)
    assert entry["special_attack"] == owned.special_attack
    assert entry["special_defense"] == owned.special_defense
    assert entry["owned_pokemon_id"] == str(owned.id)


def test_build_trainer_party_snapshot_entry_has_correct_fields():
    party = _make_party()
    entry = build_trainer_party_snapshot(party)

    owned = party.owned_pokemon
    assert entry["id"] == str(party.id)
    assert entry["hp"] == owned.hp
    assert entry["slot"] == party.slot
    assert entry["name"] == owned.name
    assert entry["speed"] == owned.speed
    assert entry["level"] == owned.level
    assert entry["max_hp"] == owned.max_hp
    assert entry["attack"] == owned.attack
    assert entry["defense"] == owned.defense
    assert entry["nickname"] == owned.nickname
    assert entry["is_active"] == party.is_active
    assert entry["experience"] == owned.experience
    assert entry["capture_rate"] == owned.pokemon.capture_rate
    assert entry["pokemon_id"] == str(owned.pokemon_id)
    assert entry["special_attack"] == owned.special_attack
    assert entry["special_defense"] == owned.special_defense
    assert entry["owned_pokemon_id"] == str(owned.id)


def test_build_trainer_party_snapshot_includes_moves():
    move = _make_move()
    party = _make_party(moves=[move])
    entry = build_trainer_party_snapshot(party)

    assert len(entry["moves"]) == 1
    assert entry["moves"][0]["name"] == move.pokemon_move.name


# ── build_wild_pokemon_snapshot ──────────────────────────────────────────────


def test_build_wild_pokemon_snapshot_returns_dict_with_expected_fields():
    wild = _make_wild_pokemon()
    result = build_wild_pokemon_snapshot(wild)

    assert result["id"] == str(wild.id)
    assert result["hp"] == wild.hp
    assert result["name"] == wild.pokemon.name
    assert result["level"] == wild.level
    assert result["speed"] == wild.speed
    assert result["attack"] == wild.attack
    assert result["max_hp"] == wild.hp
    assert result["defense"] == wild.defense
    assert result["experience"] == wild.experience
    assert result["pokemon_id"] == str(wild.pokemon_id)
    assert result["capture_rate"] == wild.pokemon.capture_rate
    assert result["special_attack"] == wild.special_attack
    assert result["special_defense"] == wild.special_defense


def test_build_wild_pokemon_snapshot_includes_up_to_4_moves():
    wild_moves = [
        SimpleNamespace(
            id=uuid4(), pp=10, name=f"move{i}", type="normal", power=40, accuracy=95
        )
        for i in range(6)
    ]
    wild = _make_wild_pokemon(moves=wild_moves)
    result = build_wild_pokemon_snapshot(wild)

    assert len(result["moves"]) == 4


def test_build_wild_pokemon_snapshot_move_fields_are_correct():
    move = SimpleNamespace(
        id=uuid4(), pp=10, name="tackle", type="normal", power=40, accuracy=100
    )
    wild = _make_wild_pokemon(moves=[move])
    result = build_wild_pokemon_snapshot(wild)

    m = result["moves"][0]
    assert m["id"] == str(move.id)
    assert m["pp"] == move.pp
    assert m["name"] == move.name
    assert m["type"] == move.type
    assert m["power"] == move.power
    assert m["max_pp"] == move.pp
    assert m["accuracy"] == move.accuracy


def test_build_payload_maps_damage_and_miss_fields_to_correct_targets():
    wild = _make_wild_pokemon()
    wild.name = wild.pokemon.name
    party = _make_party()
    progression = AttributesCalculatedSchema(
        hp=10,
        level=5,
        speed=10,
        attack=10,
        max_hp=20,
        defense=10,
        level_up=False,
        experience=10,
        special_attack=10,
        special_defense=10,
    )
    battle_result = SimpleNamespace(
        error=False,
        status=BattleSessionStatusEnum.ACTIVE,
        owned_pokemon_move_name="ember",
        wild_pokemon_move_name="tackle",
        error_message=None,
        wild_pokemon_damage=13,
        wild_pokemon_missed=True,
        wild_pokemon_fainted=False,
        wild_pokemon_progression=progression,
        owned_pokemon_damage=7,
        owned_pokemon_missed=False,
        owned_pokemon_fainted=False,
        owned_pokemon_progression=progression,
    )

    payload = build_payload(
        wild_pokemon=wild,
        trainer_active_pokemon=party.owned_pokemon,
        battle_result=battle_result,
    )

    assert payload["wild_pokemon_damage"] == 13
    assert payload["wild_pokemon_missed"] is True
    assert payload["trainer_active_pokemon_damage"] == 7
    assert payload["trainer_active_pokemon_missed"] is False


def test_resolve_battle_session_status_sets_wild_defeated_when_wild_faints():
    status = _resolve_battle_session_status(
        owned_pokemon_missed=False,
        wild_pokemon_fainted=True,
        owned_pokemon_fainted=False,
    )
    assert status == BattleSessionStatusEnum.WILD_POKEMON_DEFEATED


def test_resolve_battle_session_status_sets_trainer_defeated_when_owned_faints():
    status = _resolve_battle_session_status(
        owned_pokemon_missed=False,
        wild_pokemon_fainted=False,
        owned_pokemon_fainted=True,
    )
    assert status == BattleSessionStatusEnum.TRAINER_DEFEATED


def test_resolve_battle_session_status_sets_escaped_when_owned_misses():
    status = _resolve_battle_session_status(
        owned_pokemon_missed=True,
        wild_pokemon_fainted=False,
        owned_pokemon_fainted=False,
    )
    assert status == BattleSessionStatusEnum.ESCAPED


def _make_process_party():
    growth_rate = SimpleNamespace(formula="x")
    move = SimpleNamespace(id=uuid4(), name="ember", power=40, accuracy=100)
    owned = SimpleNamespace(
        id=uuid4(),
        name="charmander",
        hp=35,
        max_hp=35,
        attack=20,
        defense=10,
        speed=18,
        level=5,
        experience=100,
        special_attack=15,
        special_defense=12,
        pokemon=SimpleNamespace(
            capture_rate=5,
            base_experience=62,
            growth_rate=growth_rate,
        ),
        moves=[],
    )
    return SimpleNamespace(id=uuid4(), slot=1, is_active=True, owned_pokemon=owned), move


def _make_process_wild(wild_move=None):
    growth_rate = SimpleNamespace(formula="x")
    wild_move = wild_move or SimpleNamespace(id=uuid4(), name="tackle", power=35, accuracy=100)
    pokemon = SimpleNamespace(
        id=uuid4(),
        name="pidgey",
        capture_rate=255,
        base_experience=60,
        growth_rate=growth_rate,
        moves=[wild_move],
    )
    return SimpleNamespace(
        id=uuid4(),
        name="pidgey",
        pokemon_id=uuid4(),
        hp=30,
        max_hp=30,
        attack=16,
        defense=8,
        experience=80,
        speed=14,
        level=4,
        special_attack=9,
        special_defense=9,
        pokemon=pokemon,
    )


def test_process_battle_returns_error_when_move_damage_cannot_be_calculated(monkeypatch):
    party, selected_move = _make_process_party()
    wild = _make_process_wild()
    monkeypatch.setattr(
        "app.domain.trainer.battle.business._calculate_opponent_damage",
        lambda **_: None,
    )

    result = process_battle(
        move=selected_move,
        status=BattleSessionStatusEnum.ACTIVE,
        wild_pokemon=wild,
        trainer_party=party,
    )

    assert result.error is True
    assert "has no move with id" in result.error_message


def test_process_battle_returns_error_when_wild_has_no_usable_move(monkeypatch):
    party, selected_move = _make_process_party()
    wild = _make_process_wild()

    calls = iter(
        [
            OpponentDamageSchema(damage=5, missed=False, current_hp=20),
            None,
        ]
    )

    monkeypatch.setattr(
        "app.domain.trainer.battle.business._calculate_opponent_damage",
        lambda **_: next(calls),
    )
    monkeypatch.setattr(
        "app.domain.trainer.battle.business.random.sample",
        lambda *_: [SimpleNamespace(id=uuid4(), name="tackle", power=35, accuracy=100)],
    )

    result = process_battle(
        move=selected_move,
        status=BattleSessionStatusEnum.ACTIVE,
        wild_pokemon=wild,
        trainer_party=party,
    )

    assert result.error is True
    assert "has no move" in result.error_message


def test_process_battle_returns_error_when_owned_growth_rate_is_missing(monkeypatch):
    party, selected_move = _make_process_party()
    wild = _make_process_wild()
    calls = iter(
        [
            OpponentDamageSchema(damage=5, missed=False, current_hp=20),
            OpponentDamageSchema(damage=4, missed=False, current_hp=10),
        ]
    )

    monkeypatch.setattr(
        "app.domain.trainer.battle.business._calculate_opponent_damage",
        lambda **_: next(calls),
    )
    monkeypatch.setattr(
        "app.domain.trainer.battle.business.random.sample",
        lambda *_: [SimpleNamespace(id=uuid4(), name="tackle", power=35, accuracy=100)],
    )
    monkeypatch.setattr(
        "app.domain.trainer.battle.business.calculate_progression",
        lambda **_: None,
    )

    result = process_battle(
        move=selected_move,
        status=BattleSessionStatusEnum.ACTIVE,
        wild_pokemon=wild,
        trainer_party=party,
    )

    assert result.error is True
    assert "Owned Pokemon" in result.error_message


def test_process_battle_returns_error_when_wild_growth_rate_is_missing(monkeypatch):
    party, selected_move = _make_process_party()
    wild = _make_process_wild()
    calls = iter(
        [
            OpponentDamageSchema(damage=5, missed=False, current_hp=20),
            OpponentDamageSchema(damage=4, missed=False, current_hp=10),
        ]
    )
    progression = AttributesCalculatedSchema(
        hp=10,
        level=5,
        speed=10,
        attack=10,
        max_hp=20,
        defense=10,
        level_up=False,
        experience=10,
        special_attack=10,
        special_defense=10,
    )

    monkeypatch.setattr(
        "app.domain.trainer.battle.business._calculate_opponent_damage",
        lambda **_: next(calls),
    )
    monkeypatch.setattr(
        "app.domain.trainer.battle.business.random.sample",
        lambda *_: [SimpleNamespace(id=uuid4(), name="tackle", power=35, accuracy=100)],
    )
    progression_calls = iter([progression, None])
    monkeypatch.setattr(
        "app.domain.trainer.battle.business.calculate_progression",
        lambda **_: next(progression_calls),
    )

    result = process_battle(
        move=selected_move,
        status=BattleSessionStatusEnum.ACTIVE,
        wild_pokemon=wild,
        trainer_party=party,
    )

    assert result.error is True
    assert "Wild Pokemon" in result.error_message


def test_process_battle_success_when_wild_is_fainted(monkeypatch):
    party, selected_move = _make_process_party()
    wild = _make_process_wild()
    progression = AttributesCalculatedSchema(
        hp=10,
        level=5,
        speed=10,
        attack=10,
        max_hp=20,
        defense=10,
        level_up=False,
        experience=10,
        special_attack=10,
        special_defense=10,
    )
    calls = iter(
        [
            OpponentDamageSchema(damage=50, missed=False, current_hp=0),
        ]
    )
    monkeypatch.setattr(
        "app.domain.trainer.battle.business._calculate_opponent_damage",
        lambda **_: next(calls),
    )
    monkeypatch.setattr(
        "app.domain.trainer.battle.business.calculate_progression",
        lambda **_: progression,
    )

    result = process_battle(
        move=selected_move,
        status=BattleSessionStatusEnum.ACTIVE,
        wild_pokemon=wild,
        trainer_party=party,
    )

    assert result.error is False
    assert result.wild_pokemon_fainted is True
    assert result.status == BattleSessionStatusEnum.WILD_POKEMON_DEFEATED


def test_build_payload_message_paths():
    from app.domain.trainer.battle.business import build_payload_message

    assert build_payload_message(status=BattleSessionStatusEnum.ACTIVE) == "Battle in progress"
    assert build_payload_message(status=BattleSessionStatusEnum.TRAINER_DEFEATED) == "Trainer defeated"
    assert build_payload_message(status=BattleSessionStatusEnum.WILD_POKEMON_DEFEATED) == "Wild Pokemon defeated"
    assert build_payload_message(status=BattleSessionStatusEnum.ESCAPED) == "Trainer escaped"
    assert build_payload_message(error=True, error_message="boom") == "boom"
    assert build_payload_message(message="override") == "override"


def test_calculate_opponent_damage_and_helpers(monkeypatch):
    move = SimpleNamespace(accuracy=100, power=40)
    monkeypatch.setattr("app.domain.trainer.battle.business.random.randint", lambda *_: 1)
    result = _calculate_opponent_damage(
        level=5,
        attack=20,
        opponent_hp=30,
        opponent_defense=10,
        move=move,
    )

    assert result is not None
    assert result.damage > 0
    assert result.current_hp < 30
    assert _calculate_opponent_damage(1, 1, 10, 1, None) is None
    assert _missed(0) is True
    assert _calculate_damage(level=1, attack=0, defense=0, power=0) >= 1
    assert _apply_damage(hp=2, damage=10) == 0


def test_calculate_opponent_damage_returns_early_when_attack_misses(monkeypatch):
    move = SimpleNamespace(accuracy=50, power=40)
    monkeypatch.setattr("app.domain.trainer.battle.business.random.randint", lambda *_: 99)

    result = _calculate_opponent_damage(
        level=5,
        attack=20,
        opponent_hp=30,
        opponent_defense=10,
        move=move,
    )

    assert result is not None
    assert result.missed is True
    assert result.damage == 0
    assert result.current_hp == 30
