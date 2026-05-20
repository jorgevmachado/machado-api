from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import Pokedex, Pokemon, PokemonType


class PokedexRepository(BaseRepository[Pokedex]):
    model = Pokedex
    default_order_by = "pokemon.order"
    relations = (
        selectinload(Pokedex.pokemon).selectinload(Pokemon.types),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.types).selectinload(PokemonType.weaknesses),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.types).selectinload(PokemonType.strengths),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.moves),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.images),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.shape),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.habitat),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.abilities),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.evolutions),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.encounters),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.growth_rate),
        selectinload(Pokedex.trainer),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_latest_discoveries(
        self,
        trainer_id,
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
            .order_by(Pokedex.discovered_at.desc())
            .limit(limit)
        )
        for option in self.relations:
            query = query.options(option)
        result = await self.session.scalars(query)
        return result.all()
