from __future__ import annotations

from datetime import datetime
from uuid import uuid4


from app.domain.trainer.battle.schema import BattleSchema
from app.models.enums import BattleSessionStatusEnum


def _base_data(**overrides) -> dict:
    base = {
        "id": uuid4(),
        "status": BattleSessionStatusEnum.ACTIVE,
        "trainer_id": uuid4(),
        "turn_number": 0,
        "wild_pokemon_name": "pidgey",
        "wild_pokemon_level": 5,
        "wild_pokemon_snapshot": {},
        "trainer_party_snapshot": [{"slot": 1, "name": "charmander"}],
        "created_at": datetime.utcnow(),
    }
    base.update(overrides)
    return base


def test_battle_schema_accepts_list_snapshot():
    data = _base_data(trainer_party_snapshot=[{"slot": 1, "name": "charmander"}])
    schema = BattleSchema(**data)
    assert isinstance(schema.trainer_party_snapshot, list)
    assert len(schema.trainer_party_snapshot) == 1


def test_battle_schema_normalizes_dict_snapshot_to_list():
    snapshot_dict = {"slot": 1, "name": "charmander"}
    data = _base_data(trainer_party_snapshot=snapshot_dict)
    schema = BattleSchema(**data)

    assert isinstance(schema.trainer_party_snapshot, list)
    assert schema.trainer_party_snapshot[0] == snapshot_dict


def test_battle_schema_preserves_existing_list():
    snapshots = [{"slot": 1}, {"slot": 2}]
    data = _base_data(trainer_party_snapshot=snapshots)
    schema = BattleSchema(**data)
    assert schema.trainer_party_snapshot == snapshots


def test_battle_schema_validates_from_attributes():
    from types import SimpleNamespace

    obj = SimpleNamespace(
        id=uuid4(),
        logs=[],
        status=BattleSessionStatusEnum.ACTIVE,
        trainer_id=uuid4(),
        turn_number=0,
        wild_pokemon_name="pidgey",
        wild_pokemon_level=5,
        wild_pokemon_snapshot={},
        trainer_party_snapshot=[{"slot": 1}],
        created_at=datetime.utcnow(),
        updated_at=None,
        deleted_at=None,
    )
    schema = BattleSchema.model_validate(obj)
    assert schema.wild_pokemon_name == "pidgey"
