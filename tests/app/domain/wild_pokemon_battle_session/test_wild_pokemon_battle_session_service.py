from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.wild_pokemon_battle_session.schema import (
    SwitchBattlePokemonSchema,
    UseBattleMoveSchema,
)
from app.domain.trainer.wild_pokemon_battle_session.service import (
    WildPokemonBattleSessionService,
)
from app.models.enums import BattleSessionStatusEnum


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


def build_move(name="tackle", power=8, pp=10):
    return SimpleNamespace(
        id=uuid4(),
        pp=pp,
        max_pp=pp,
        pokemon_move_id=uuid4(),
        pokemon_move_name=name,
        pokemon_move_type="normal",
        pokemon_move_power=power,
        pokemon_move_accuracy=100,
    )


def build_trainer():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        pokeballs=5,
        capture_rate=80,
    )


def build_party_member(trainer, name="bulbasaur", slot=1, hp=20, move_power=8):
    my_pokemon = SimpleNamespace(
        id=uuid4(),
        name=f"{name}-owned",
        nickname=name.title(),
        level=5,
        experience=0,
        hp=hp,
        max_hp=hp,
        attack=12,
        defense=9,
        special_attack=10,
        special_defense=10,
        speed=10,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        pokemon=SimpleNamespace(id=uuid4(), name=name),
        trainer=trainer,
        moves=[build_move(power=move_power)],
    )
    return SimpleNamespace(
        id=uuid4(),
        slot=slot,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
        my_pokemon=my_pokemon,
    )


def build_wild_pokemon(name="pikachu", hp=15, move_power=5):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        hp=hp,
        attack=11,
        defense=8,
        special_attack=10,
        special_defense=8,
        speed=11,
        moves=[
            SimpleNamespace(
                id=uuid4(),
                name="scratch",
                type="normal",
                power=move_power,
                accuracy=100,
                pp=15,
            )
        ],
    )


class FakeRepository:
    def __init__(self):
        self.session = FakeSession()
        self.active_session = None
        self.logs = []
        self.turns = []

    async def find_active_by_trainer_id(self, _trainer_id):
        return self.active_session

    async def create_session(self, entity):
        self.active_session = entity
        return entity

    async def create_turn(self, entity):
        self.turns.append(entity)
        return entity

    async def create_log(self, entity):
        self.logs.append(entity)
        return entity

    async def list_logs(self, _battle_session_id):
        return self.logs


class FakeTrainerPartyService:
    def __init__(self, party):
        self.party = party

    async def get_party_by_trainer_id(self, _trainer_id):
        return self.party


class FakePokemonService:
    def __init__(self, pokemon):
        self.pokemon = pokemon

    async def find_detail(self, _identifier):
        return self.pokemon


def build_service(*, party, wild_pokemon):
    repository = FakeRepository()
    service = WildPokemonBattleSessionService(
        repository,
        trainer_party_service=FakeTrainerPartyService(party),
        pokemon_service=FakePokemonService(wild_pokemon),
    )
    return service, repository


@pytest.mark.asyncio
async def test_create_or_resume_battle_creates_new_active_session():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)

    result = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    assert result.status == BattleSessionStatusEnum.ACTIVE
    assert result.trainer_active_my_pokemon_id == party[0].my_pokemon.id
    assert repository.active_session is result
    assert len(repository.logs) == 1


@pytest.mark.asyncio
async def test_from_session_and_has_active_battle_cover_factory_helpers():
    service = WildPokemonBattleSessionService.from_session(AsyncMock())
    service.repository.find_active_by_trainer_id = AsyncMock(return_value=SimpleNamespace())

    assert service is not None
    assert await service.has_active_battle(uuid4()) is True


@pytest.mark.asyncio
async def test_create_or_resume_battle_returns_existing_session():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    repository.active_session = SimpleNamespace(id=uuid4())

    result = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    assert result is repository.active_session


@pytest.mark.asyncio
async def test_use_move_processes_trainer_attack_and_wild_response():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon(hp=18)
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )
    move_id = session.trainer_party_snapshot[0]["moves"][0]["id"]

    result = await service.use_move(
        trainer,
        UseBattleMoveSchema(move_id=move_id),
    )

    assert result.turn_number == 1
    assert result.wild_side.current_hp < result.wild_side.max_hp
    assert result.trainer_side.current_hp < result.trainer_side.max_hp
    assert repository.session.commits == 1
    assert len(repository.turns) == 2


@pytest.mark.asyncio
async def test_service_uses_repository_party_fallback_without_public_service():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    repository = FakeRepository()
    repository_party = AsyncMock()
    repository_party.list_active_party.return_value = party
    service = WildPokemonBattleSessionService(
        repository,
        trainer_party_service=None,
        pokemon_service=FakePokemonService(wild_pokemon),
    )
    service.trainer_party_repository = repository_party

    with patch(
        'app.domain.trainer.wild_pokemon_battle_session.service.TrainerPartyService.to_party_schema',
        side_effect=lambda entity: entity,
    ):
        result = await service.create_or_resume_battle(
            trainer=trainer,
            exploration_event=SimpleNamespace(id=uuid4()),
            wild_pokemon=wild_pokemon,
        )

    assert result.trainer_active_my_pokemon_id == party[0].my_pokemon.id


@pytest.mark.asyncio
async def test_switch_pokemon_raises_for_active_member():
    trainer = build_trainer()
    party = [build_party_member(trainer), build_party_member(trainer, name="charmander", slot=2)]
    wild_pokemon = build_wild_pokemon()
    service, _repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.switch_pokemon(
            trainer,
            SwitchBattlePokemonSchema(my_pokemon_id=session.trainer_active_my_pokemon_id),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_active_battle_and_list_logs_raise_when_missing():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    repository.active_session = None

    with pytest.raises(HTTPException) as active_exc:
        await service.get_active_battle(trainer)
    with pytest.raises(HTTPException) as logs_exc:
        await service.list_logs(trainer)

    assert active_exc.value.status_code == 404
    assert logs_exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_active_battle_returns_serialized_session():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, _repository = build_service(party=party, wild_pokemon=wild_pokemon)
    await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    result = await service.get_active_battle(trainer)

    assert result.id is not None


@pytest.mark.asyncio
async def test_use_move_raises_when_move_has_no_pp():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    party[0].my_pokemon.moves[0].pp = 0
    wild_pokemon = build_wild_pokemon()
    service, _repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )
    move_id = session.trainer_party_snapshot[0]["moves"][0]["id"]

    with pytest.raises(HTTPException) as exc_info:
        await service.use_move(
            trainer,
            UseBattleMoveSchema(move_id=move_id),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_use_move_marks_battle_as_won_when_wild_faints():
    trainer = build_trainer()
    party = [build_party_member(trainer, move_power=20)]
    wild_pokemon = build_wild_pokemon(hp=10)
    service, _repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )
    move_id = session.trainer_party_snapshot[0]["moves"][0]["id"]

    result = await service.use_move(
        trainer,
        UseBattleMoveSchema(move_id=move_id),
    )

    assert result.status == BattleSessionStatusEnum.WON
    assert result.wild_side.current_hp == 0


@pytest.mark.asyncio
async def test_switch_pokemon_processes_wild_response():
    trainer = build_trainer()
    party = [build_party_member(trainer), build_party_member(trainer, name="charmander", slot=2)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    result = await service.switch_pokemon(
        trainer,
        SwitchBattlePokemonSchema(my_pokemon_id=party[1].my_pokemon.id),
    )

    assert result.trainer_active_my_pokemon_id == party[1].my_pokemon.id
    assert repository.session.commits == 1


@pytest.mark.asyncio
async def test_use_move_raises_when_active_pokemon_cannot_be_resolved():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )
    session.trainer_active_my_pokemon_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        service.to_schema(session)

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_process_wild_response_returns_early_for_inactive_status_and_fainted_member():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    session.status = BattleSessionStatusEnum.WON
    await service._process_wild_response(session)

    session.status = BattleSessionStatusEnum.ACTIVE
    session.trainer_party_snapshot[0]['current_hp'] = 0
    await service._process_wild_response(session)

    assert session.status == BattleSessionStatusEnum.LOST


@pytest.mark.asyncio
async def test_flee_marks_battle_as_fled():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    result = await service.flee(trainer)

    assert result.status == BattleSessionStatusEnum.FLED
    assert repository.session.commits == 1
    assert repository.logs[-1].payload["status"] == BattleSessionStatusEnum.FLED.value


@pytest.mark.asyncio
async def test_list_logs_returns_created_logs():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, _repository = build_service(party=party, wild_pokemon=wild_pokemon)
    await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    result = await service.list_logs(trainer)

    assert len(result) == 1
    assert result[0].log_type == 'SESSION_STARTED'


@pytest.mark.asyncio
async def test_get_active_entity_and_to_turn_schema_cover_helpers():
    trainer = build_trainer()
    party = [build_party_member(trainer)]
    wild_pokemon = build_wild_pokemon()
    service, repository = build_service(party=party, wild_pokemon=wild_pokemon)
    session = await service.create_or_resume_battle(
        trainer=trainer,
        exploration_event=SimpleNamespace(id=uuid4()),
        wild_pokemon=wild_pokemon,
    )

    entity = await service._get_active_entity(trainer.id)
    assert entity is session

    turn = SimpleNamespace(
        id=uuid4(),
        turn_number=1,
        actor='TRAINER',
        action_type='USE_MOVE',
        move_name='tackle',
        payload={},
        created_at=datetime.now(timezone.utc),
    )
    schema = service.to_turn_schema(turn)
    assert schema.turn_number == 1

    repository.active_session = None
    with pytest.raises(HTTPException) as exc_info:
        await service._get_active_entity(trainer.id)

    assert exc_info.value.status_code == 404
