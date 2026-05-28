from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.auth.schema import RegisterSchema
from app.models.enums import GenderEnum


def test_register_schema_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterSchema(
            name="Ash",
            email="ash@example.com",
            username="ash",
            gender=GenderEnum.MALE,
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            password="short",
        )
