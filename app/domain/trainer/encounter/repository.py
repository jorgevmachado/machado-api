from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import (
    ExplorationEvent,
    Pokemon,
    PokemonEncounter,
    PokemonType,
    TrainerEncounter,
)


class TrainerEncounterRepository(BaseRepository[TrainerEncounter]):
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

    async def find_active_trainer_encounter(
            self,
            trainer_id: UUID,
    ) -> TrainerEncounter | None:
        return await self.find_by(
            trainer_id=trainer_id,
            is_active=True,
        )

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
