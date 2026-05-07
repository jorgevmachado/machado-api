from __future__ import annotations

from typing import Any

import httpx

from app.core.settings import Settings
from app.infrastructure.external_api.schemas import (
    PokeApiPayloadSchema,
    PokemonExternalAbilitySchema,
    PokemonExternalEvolutionSchema,
    PokemonExternalGrowthRateSchema,
    PokemonExternalListSchema,
    PokemonExternalMoveSchema,
    PokemonExternalSchema,
    PokemonExternalSpeciesSchema,
    PokemonExternalTypeSchema,
    PokemonExternalMoveDamageClassSchema,
)


class PokeApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        verify: bool | str | None = None,
        timeout: float = 30,
    ) -> None:
        settings = Settings()
        self.base_url = (base_url or settings.POKEAPI_BASE_URL).rstrip("/")
        if verify is None:
            verify = settings.POKEAPI_CA_BUNDLE or settings.POKEAPI_VERIFY_SSL
        self.verify = verify
        self.timeout = timeout

    async def _get(self, path_or_url: str) -> dict[str, Any] | list[dict[str, Any]]:
        url = (
            path_or_url
            if path_or_url.startswith("http")
            else f"{self.base_url}/{path_or_url.lstrip('/')}"
        )
        async with httpx.AsyncClient(
            verify=self.verify, timeout=self.timeout
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def get_resource_url(self, url: str) -> PokeApiPayloadSchema:
        payload = await self._get(url)
        if not isinstance(payload, dict):
            return PokeApiPayloadSchema()
        return PokeApiPayloadSchema.model_validate(payload)

    async def list_pokemon(
        self, offset: int = 0, limit: int = 1350
    ) -> PokemonExternalListSchema:
        payload = await self._get(f"pokemon?offset={offset}&limit={limit}")
        return PokemonExternalListSchema.model_validate(payload)

    async def get_pokemon(self, name_or_id: str | int) -> PokemonExternalSchema:
        payload = await self._get(f"pokemon/{name_or_id}")
        return PokemonExternalSchema.model_validate(payload)

    async def get_pokemon_species(
        self, name_or_id: str | int
    ) -> PokemonExternalSpeciesSchema:
        payload = await self._get(f"pokemon-species/{name_or_id}")
        return PokemonExternalSpeciesSchema.model_validate(payload)

    async def get_pokemon_encounters(
        self, name_or_id: str | int
    ) -> list[dict[str, Any]]:
        payload = await self._get(f"pokemon/{name_or_id}/encounters")
        return payload if isinstance(payload, list) else []

    async def get_move(self, name_or_id: str | int) -> PokemonExternalMoveSchema:
        payload = await self._get(f"move/{name_or_id}")
        return PokemonExternalMoveSchema.model_validate(payload)

    async def get_type(self, name_or_id: str | int) -> PokemonExternalTypeSchema:
        payload = await self._get(f"type/{name_or_id}")
        return PokemonExternalTypeSchema.model_validate(payload)

    async def get_ability(self, name_or_id: str | int) -> PokemonExternalAbilitySchema:
        payload = await self._get(f"ability/{name_or_id}")
        return PokemonExternalAbilitySchema.model_validate(payload)

    async def get_growth_rate(
        self, name_or_id: str | int
    ) -> PokemonExternalGrowthRateSchema:
        payload = await self._get(f"growth-rate/{name_or_id}")
        return PokemonExternalGrowthRateSchema.model_validate(payload)

    async def get_evolution_chain_by_url(
        self, url: str
    ) -> PokemonExternalEvolutionSchema:
        payload = await self._get(url)
        return PokemonExternalEvolutionSchema.model_validate(payload)

    async def get_move_damage_class_by_url(
        self, url: str
    ) -> PokemonExternalMoveDamageClassSchema:
        payload = await self._get(url)
        return PokemonExternalMoveDamageClassSchema.model_validate(payload)
