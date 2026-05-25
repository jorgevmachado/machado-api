from __future__ import annotations
from uuid import UUID
import logging
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.pokedex.business import build_initial_pokedex_attributes
from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.models import Pokedex, Trainer, Pokemon
from app.models.common import utcnow

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class PokedexService(BaseService[PokedexRepository, Pokedex]):
    def __init__(
            self,
            repository: PokedexRepository,
            trainer_service: TrainerService | None = None,
            pokemon_service: PokemonService | None = None,
    ) -> None:
        super().__init__(
            alias="Pokedex",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokedexService", operation="pokedex"
            ),
            schema_class=PokedexSchema,
            cache_prefix="pokedex",
        )
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        if pokemon_service is None:
            from app.domain.pokemon.service import PokemonService

            pokemon_service = PokemonService.from_session(session)
        self.pokemon_service = pokemon_service
        self.list_cache_service = self.cache_service

    async def is_discovered(
            self,
            *,
            trainer_id: UUID,
            pokemon_name: str,
    ) -> bool:
        entity = await self.repository.find_by(
            trainer_id=trainer_id,
            name=pokemon_name,
        )
        return bool(entity and entity.discovered)

    async def discover(
            self,
            trainer: Trainer,
            pokemon_name: str,
            commit: bool = True,
    ) -> Pokedex:
        entity = await self.repository.find_by(
            trainer_id=trainer.id,
            name=pokemon_name,
        )
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Pokedex entry not found",
            )

        if not entity.discovered:
            await self.pokemon_service.find_detail(identifier=pokemon_name.lower())
            entity.discovered = True
            entity.discovered_at = utcnow()
            await self.repository.session.flush()

        fresh = await self.repository.find_by(
            trainer_id=trainer.id,
            name=pokemon_name,
        )
        if fresh is None:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Could not load discovered Pokedex entry",
            )
        if commit:
            await self.repository.session.commit()
            await self._invalidate_cache(
                trainer_id=str(trainer.id),
                identifier=str(entity.id)
            )
        return fresh

    async def initialize_for_trainer(
            self,
            *,
            trainer_id,
            discovered_pokemon_name: str,
            discovered_at: datetime | None = None,
            commit: bool = True,
    ) -> list[Pokedex]:
        pokemon_list: list[Pokemon] = []
        pokemons = await self.pokemon_service.list_all()
        if isinstance(pokemons, list):
            pokemon_list = pokemons
        attributes_by_pokemon_id = {
            pokemon.id: build_initial_pokedex_attributes(pokemon)
            for pokemon in pokemon_list
        }

        await self._create_for_trainer(
            trainer_id=trainer_id,
            pokemons=pokemon_list,
            discovered_pokemon_name=discovered_pokemon_name,
            discovered_at=discovered_at,
            attributes_by_pokemon_id=attributes_by_pokemon_id,
        )

        if commit:
            await self.repository.session.commit()

        result: list[Pokedex] = []
        for pokemon in pokemon_list:
            entity = await self.repository.find_by(
                trainer_id=trainer_id,
                name=pokemon.name,
            )
            if entity is not None:
                result.append(entity)

        if commit:
            await self._invalidate_cache(
                identifier=discovered_pokemon_name,
                trainer_id=str(trainer_id),
            )
        return result

    async def list_latest_discoveries(
            self,
            trainer_id: UUID,
            limit: int = 3,
    ) -> list[Pokedex]:
        return await self.repository.list_latest_discoveries(
            trainer_id=trainer_id,
            limit=limit,
        )

    async def _create_for_trainer(
            self,
            *,
            trainer_id: UUID,
            pokemons: list[Pokemon],
            discovered_pokemon_name: str | None = None,
            discovered_at: datetime | None = None,
            attributes_by_pokemon_id: dict[UUID, dict[str, int]],
    ) -> list[Pokedex]:
        entries: list[Pokedex] = []

        for pokemon in pokemons:
            entries.append(
                await self.repository.save(
                    entity=Pokedex(
                        trainer_id=trainer_id,
                        pokemon_id=pokemon.id,
                        nickname=None,
                        discovered=discovered_pokemon_name == pokemon.name,
                        discovered_at=(
                            discovered_at if discovered_pokemon_name == pokemon.name else None
                        ),
                        **attributes_by_pokemon_id[pokemon.id],
                    )
                )
            )
        return entries
