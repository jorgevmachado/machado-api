from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.domain.pokemon.type.schema import TypeSchema
from app.models import PokemonStatusEnum


class TestTypeSchema:
    @staticmethod
    def test_serialize_transforms_strengths_and_weaknesses() -> None:
        now = datetime.now(timezone.utc)
        base_payload = {
            "id": uuid4(),
            "name": "grass",
            "url": "https://pokeapi.co/api/v2/type/12/",
            "order": 12,
            "status": PokemonStatusEnum.COMPLETE,
            "text_color": "#fff",
            "badge_url": "badge-url",
            "description": "desc",
            "badge_icon_url": "badge-icon-url",
            "background_color": "#000",
            "badge_shield_url": "shield-url",
            "badge_legends_url": "legend-url",
            "badge_legend_icon_url": "legend-icon-url",
            "badge_shield_icon_url": "shield-icon-url",
            "created_at": now,
            "updated_at": None,
            "deleted_at": None,
        }
        schema = TypeSchema.model_validate(
            {
                **base_payload,
                "weaknesses": [{**base_payload, "id": uuid4(), "name": "water"}],
                "strengths": [{**base_payload, "id": uuid4(), "name": "fire"}],
            }
        )

        serialized = schema.serialize()

        assert serialized["weaknesses"][0]["name"] == "water"
        assert serialized["strengths"][0]["name"] == "fire"
