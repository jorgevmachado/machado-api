from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.encounter.repository import EncounterRepository
from app.domain.pokemon.encounter.schema import (
    EncounterSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Encounter
from app.shared.utils.number import ensure_order_number

logger = logging.getLogger(__name__)


class EncounterService(BaseService[EncounterRepository, Encounter]):
    def __init__(
        self,
        repository: EncounterRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="Encounter",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="EncounterService", operation="pokemon.encounter"
            ),
            schema_class=EncounterSchema,
            cache_prefix="encounter",
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        client: PokeApiClient | None = None,
    ):
        return cls(EncounterRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[Encounter]:
        synced: list[Encounter] = []
        for entry in resources:
            encounter = await self.get_or_create(entry=entry)
            if encounter is None:
                continue
            synced.append(encounter)
        return synced

    async def get_or_create(self, entry: dict | None) -> Encounter | None:
        if not entry:
            raise ValueError("Entry cannot be None when creating a new Encounter")

        resource = entry.get("location_area") or entry

        if not resource:
            raise ValueError("Entry cannot be None when creating a new Encounter")

        url = resource.get("url")
        order = ensure_order_number(url)

        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        name = resource.get("name")

        if name is None or url is None:
            raise ValueError(
                "Name and URL cannot be None when creating a new Encounter"
            )

        version_details = entry.get("version_details", [])
        if not version_details:
            raise ValueError(
                "Encounter details are missing required fields: version_details"
            )

        version_detail = version_details[0]
        max_chance = version_detail.get("max_chance", 0)
        version = version_detail.get("version", None)
        if not version:
            raise ValueError("Encounter details are missing required fields: version")

        version_name = version.get("name", None)
        if not version_name:
            raise ValueError(
                "Encounter details are missing required fields: version name"
            )

        encounter_details = version_detail.get("encounter_details", [])
        if not encounter_details:
            raise ValueError(
                "Encounter details are missing required fields: encounter_details"
            )

        encounter_detail = encounter_details[0]

        if not encounter_detail:
            raise ValueError("Encounter details are missing required fields")

        method = encounter_detail.get("method", None)
        if not method:
            raise ValueError("Encounter details are missing required fields: method")
        method_name = method.get("name", None)
        if not method_name:
            raise ValueError(
                "Encounter details are missing required fields: method name"
            )

        condition_values = encounter_detail.get("condition_values", [])
        condition_name = ""
        if condition_values:
            condition_value = condition_values[0]
            condition_name = condition_value.get("name", "")

        chance = encounter_detail.get("chance", 0)
        max_level = encounter_detail.get("max_level", 0)
        min_level = encounter_detail.get("min_level", 0)

        return await self.repository.save(
            entity=Encounter(
                url=url,
                name=name,
                order=order,
                chance=chance,
                method=method_name,
                version=version_name,
                min_level=min_level,
                max_level=max_level,
                condition=condition_name,
                max_chance=max_chance,
            )
        )
