from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.domain.trainer.battle.business import (
    build_snapshot_move,
    build_trainer_party_snapshot,
    build_wild_pokemon_snapshot,
)


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
    return SimpleNamespace(id=uuid4(),slot=1, is_active=True, owned_pokemon=owned)


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


def test_build_trainer_party_snapshot_returns_list_with_one_entry():
    move = _make_move()
    party = _make_party(moves=[move])
    result = build_trainer_party_snapshot(party)

    assert isinstance(result, list)
    assert len(result) == 1


def test_build_trainer_party_snapshot_entry_has_correct_fields():
    party = _make_party()
    entry = build_trainer_party_snapshot(party)[0]

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
    entry = build_trainer_party_snapshot(party)[0]

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
