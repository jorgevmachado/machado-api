from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import (
    ExplorationEvent,
    MyPokemon,
    MyPokemonMove,
    Pokedex,
    Pokemon,
    PokemonEncounter,
    PokemonType,
    Trainer,
    TrainerEncounter,
    TrainerParty,
)


class TrainerExplorationRepository(BaseRepository[TrainerEncounter]):
    model = TrainerEncounter
    default_order_by = "pokemon_encounter.order"
    relations = (
        selectinload(TrainerEncounter.pokemon_encounter)
        .selectinload(PokemonEncounter.pokemons)
        .selectinload(Pokemon.types),
        selectinload(TrainerEncounter.pokemon_encounter)
        .selectinload(PokemonEncounter.pokemons)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.weaknesses),
        selectinload(TrainerEncounter.pokemon_encounter)
        .selectinload(PokemonEncounter.pokemons)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.strengths),
        selectinload(TrainerEncounter.pokemon_encounter).selectinload(
            PokemonEncounter.pokemons
        ),
        selectinload(TrainerEncounter.trainer),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_encounters_for_pokemon(self, pokemon_name: str) -> list[PokemonEncounter]:
        query = (
            select(PokemonEncounter)
            .join(PokemonEncounter.pokemons)
            .where(
                Pokemon.name == pokemon_name,
                Pokemon.deleted_at.is_(None),
                PokemonEncounter.deleted_at.is_(None),
            )
            .options(selectinload(PokemonEncounter.pokemons))
            .order_by(PokemonEncounter.order)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def create_known_encounters(
        self,
        *,
        trainer_id: UUID,
        encounters: list[PokemonEncounter],
        active_encounter_id: UUID | None,
    ) -> list[TrainerEncounter]:
        entities: list[TrainerEncounter] = []
        for encounter in encounters:
            entity = TrainerEncounter(
                trainer_id=trainer_id,
                pokemon_encounter_id=encounter.id,
                is_active=encounter.id == active_encounter_id,
            )
            entities.append(entity)
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def list_trainer_encounters(self, trainer_id: UUID) -> list[TrainerEncounter]:
        query = (
            select(TrainerEncounter)
            .join(TrainerEncounter.pokemon_encounter)
            .where(
                TrainerEncounter.trainer_id == trainer_id,
                TrainerEncounter.deleted_at.is_(None),
                PokemonEncounter.deleted_at.is_(None),
            )
            .order_by(PokemonEncounter.order)
        )
        for option in self.relations:
            query = query.options(option)
        result = await self.session.scalars(query)
        return result.all()

    async def find_trainer_encounter(
        self,
        trainer_id: UUID,
        encounter_id: UUID,
    ) -> TrainerEncounter | None:
        query = (
            select(TrainerEncounter)
            .where(
                TrainerEncounter.trainer_id == trainer_id,
                TrainerEncounter.id == encounter_id,
                TrainerEncounter.deleted_at.is_(None),
            )
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def find_active_trainer_encounter(
        self,
        trainer_id: UUID,
    ) -> TrainerEncounter | None:
        query = (
            select(TrainerEncounter)
            .where(
                TrainerEncounter.trainer_id == trainer_id,
                TrainerEncounter.is_active.is_(True),
                TrainerEncounter.deleted_at.is_(None),
            )
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def deactivate_all_encounters(self, trainer_id: UUID) -> None:
        result = await self.session.scalars(
            select(TrainerEncounter).where(
                TrainerEncounter.trainer_id == trainer_id,
                TrainerEncounter.deleted_at.is_(None),
            )
        )
        for entity in result.all():
            entity.is_active = False
        await self.session.flush()

    async def list_active_party(self, trainer_id: UUID) -> list[TrainerParty]:
        query = (
            select(TrainerParty)
            .join(TrainerParty.my_pokemon)
            .where(
                TrainerParty.trainer_id == trainer_id,
                TrainerParty.deleted_at.is_(None),
                TrainerParty.is_active.is_(True),
                MyPokemon.deleted_at.is_(None),
            )
            .options(
                selectinload(TrainerParty.my_pokemon)
                .selectinload(MyPokemon.pokemon)
                .selectinload(Pokemon.types),
                selectinload(TrainerParty.my_pokemon)
                .selectinload(MyPokemon.pokemon)
                .selectinload(Pokemon.types)
                .selectinload(PokemonType.weaknesses),
                selectinload(TrainerParty.my_pokemon)
                .selectinload(MyPokemon.pokemon)
                .selectinload(Pokemon.types)
                .selectinload(PokemonType.strengths),
                selectinload(TrainerParty.my_pokemon).selectinload(MyPokemon.trainer),
                selectinload(TrainerParty.my_pokemon)
                .selectinload(MyPokemon.moves)
                .selectinload(MyPokemonMove.pokemon_move),
            )
            .order_by(TrainerParty.slot)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def soft_delete_active_party(self, trainer_id: UUID, deleted_at: datetime) -> None:
        result = await self.session.scalars(
            select(TrainerParty).where(
                TrainerParty.trainer_id == trainer_id,
                TrainerParty.deleted_at.is_(None),
                TrainerParty.is_active.is_(True),
            )
        )
        for entity in result.all():
            entity.is_active = False
            entity.deleted_at = deleted_at
        await self.session.flush()

    async def list_owned_my_pokemon(
        self,
        trainer_id: UUID,
        my_pokemon_ids: list[UUID],
    ) -> list[MyPokemon]:
        if not my_pokemon_ids:
            return []
        query = (
            select(MyPokemon)
            .where(
                MyPokemon.trainer_id == trainer_id,
                MyPokemon.deleted_at.is_(None),
                MyPokemon.id.in_(my_pokemon_ids),
            )
            .options(
                selectinload(MyPokemon.pokemon).selectinload(Pokemon.types),
                selectinload(MyPokemon.pokemon)
                .selectinload(Pokemon.types)
                .selectinload(PokemonType.weaknesses),
                selectinload(MyPokemon.pokemon)
                .selectinload(Pokemon.types)
                .selectinload(PokemonType.strengths),
                selectinload(MyPokemon.trainer),
                selectinload(MyPokemon.moves).selectinload(MyPokemonMove.pokemon_move),
            )
        )
        result = await self.session.scalars(query)
        return result.all()

    async def create_party(
        self,
        *,
        trainer_id: UUID,
        my_pokemons: list[MyPokemon],
    ) -> list[TrainerParty]:
        entities: list[TrainerParty] = []
        for slot, my_pokemon in enumerate(my_pokemons, start=1):
            entity = TrainerParty(
                trainer_id=trainer_id,
                my_pokemon_id=my_pokemon.id,
                slot=slot,
                is_active=True,
            )
            entities.append(entity)
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def create_event(
        self,
        *,
        trainer_id: UUID,
        event_type,
        payload: dict,
    ) -> ExplorationEvent:
        entity = ExplorationEvent(
            trainer_id=trainer_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def find_trainer(self, trainer_id: UUID) -> Trainer | None:
        return await self.session.scalar(
            select(Trainer).where(
                Trainer.id == trainer_id,
                Trainer.deleted_at.is_(None),
            )
        )

    async def list_latest_discoveries(
        self,
        trainer_id: UUID,
        limit: int = 3,
    ) -> list[Pokedex]:
        query = (
            select(Pokedex)
            .join(Pokedex.pokemon)
            .where(
                Pokedex.trainer_id == trainer_id,
                Pokedex.deleted_at.is_(None),
                Pokedex.discovered.is_(True),
                Pokedex.discovered_at.is_not(None),
                Pokemon.deleted_at.is_(None),
            )
            .options(
                selectinload(Pokedex.pokemon).selectinload(Pokemon.types),
                selectinload(Pokedex.pokemon)
                .selectinload(Pokemon.types)
                .selectinload(PokemonType.weaknesses),
                selectinload(Pokedex.pokemon)
                .selectinload(Pokemon.types)
                .selectinload(PokemonType.strengths),
                selectinload(Pokedex.trainer),
            )
            .order_by(Pokedex.discovered_at.desc())
            .limit(limit)
        )
        result = await self.session.scalars(query)
        return result.all()
