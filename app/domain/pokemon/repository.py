from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import (
    Pokemon,
    PokemonType,
)
from app.shared.schemas import FilterPage
from app.shared.utils.string import is_valid_uuid


class PokemonRepository(BaseRepository[Pokemon]):
    model = Pokemon
    default_order_by = "order"
    relations = (
        selectinload(Pokemon.types),
        selectinload(Pokemon.types).selectinload(PokemonType.weaknesses),
        selectinload(Pokemon.types).selectinload(PokemonType.strengths),
        selectinload(Pokemon.moves),
        selectinload(Pokemon.abilities),
        selectinload(Pokemon.evolutions),
        selectinload(Pokemon.images),
        selectinload(Pokemon.growth_rate),
        selectinload(Pokemon.habitat),
        selectinload(Pokemon.shape),
        selectinload(Pokemon.encounters),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def _apply_filters(self, query, page_filter: FilterPage | None):
        if page_filter is None:
            return query

        filters = page_filter.model_dump(exclude_none=True)
        name = filters.get("name")
        order = filters.get("order")
        status = filters.get("status")
        pokemon_type = filters.get("type") or filters.get("type")

        query = query.where(Pokemon.deleted_at.is_(None))
        if name:
            query = query.where(Pokemon.name.ilike(f"%{name}%"))
        if order is not None:
            query = query.where(Pokemon.order == int(order))
        if status:
            query = query.where(Pokemon.status == status)
        if pokemon_type:
            query = query.where(Pokemon.types.any(PokemonType.name == pokemon_type))

        return query

    async def has_any(self) -> bool:
        total = await self.session.scalar(
            select(func.count())
            .select_from(Pokemon)
            .where(Pokemon.deleted_at.is_(None))
        )
        return bool(total)

    async def get_by_order(self, order: int) -> Pokemon | None:
        return await self.session.scalar(select(Pokemon).where(Pokemon.order == order))

    async def list_by_names(self, names: set[str]) -> list[Pokemon]:
        if not names:
            return []
        result = await self.session.scalars(
            select(Pokemon).where(Pokemon.name.in_(names))
        )
        return result.all()

    async def create_minimal(
        self, *, name: str, order: int, external_image: str
    ) -> Pokemon:
        pokemon = Pokemon(name=name, order=order, external_image=external_image)
        self.session.add(pokemon)
        await self.session.flush()
        return pokemon

    async def find_detail(self, identifier: str) -> Pokemon | None:
        if identifier.isdigit():
            return await self.find_by(order=int(identifier))

        if is_valid_uuid(identifier):
            return await self.find_by(id=UUID(identifier))

        return await self.find_by(name=identifier)
