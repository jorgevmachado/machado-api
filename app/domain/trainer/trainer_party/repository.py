from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import MyPokemon, MyPokemonMove, Pokemon, PokemonType, TrainerParty


class TrainerPartyRepository(BaseRepository[TrainerParty]):
    model = TrainerParty
    default_order_by = "slot"
    relations = (
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

    def __init__(self, session: AsyncSession):
        super().__init__(session)

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
            .order_by(TrainerParty.slot)
        )
        for option in self.relations:
            query = query.options(option)
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
