from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository.base import BaseRepository
from app.models import PokemonImage


class PokemonImageRepository(BaseRepository[PokemonImage]):
    model = PokemonImage

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def replace_for_pokemon(
        self, pokemon_id: UUID, images: list[PokemonImage]
    ) -> list[PokemonImage]:
        await self.session.execute(
            delete(PokemonImage).where(PokemonImage.pokemon_id == pokemon_id)
        )
        for image in images:
            self.session.add(image)
        await self.session.flush()
        return images
