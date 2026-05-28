from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.auth.schema import LoginSchema, RegisterSchema
from app.domain.auth.service import AuthService
from app.models.enums import GenderEnum, StatusEnum


def build_register_schema() -> RegisterSchema:
    return RegisterSchema(
        name="Ash Ketchum",
        email="ash@example.com",
        username="ash",
        gender=GenderEnum.MALE,
        date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
        password="pikachu123",
    )


class TestAuthService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_register_rejects_existing_email():
        repository = AsyncMock()
        repository.get_by_email.return_value = object()
        service = AuthService(repository=repository)

        with pytest.raises(HTTPException) as exc_info:
            await service.register(build_register_schema())

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert exc_info.value.detail == "Email already registered"

    @staticmethod
    @pytest.mark.asyncio
    async def test_register_rejects_existing_username():
        repository = AsyncMock()
        repository.get_by_email.return_value = None
        repository.get_by_username.return_value = object()
        service = AuthService(repository=repository)

        with pytest.raises(HTTPException) as exc_info:
            await service.register(build_register_schema())

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert exc_info.value.detail == "Username already taken"

    @staticmethod
    @pytest.mark.asyncio
    async def test_register_creates_hashed_user(monkeypatch):
        repository = AsyncMock()
        repository.get_by_email.return_value = None
        repository.get_by_username.return_value = None
        created = SimpleNamespace(id=uuid4())
        repository.create.return_value = created
        monkeypatch.setattr(
            "app.domain.auth.service.get_password_hash", lambda _: "hashed-password"
        )
        service = AuthService(repository=repository)

        result = await service.register(build_register_schema())

        assert result is created
        repository.create.assert_awaited_once()
        payload = repository.create.await_args.args[0]
        assert payload["password"] == "hashed-password"
        assert payload["status"] == StatusEnum.ACTIVE

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_rejects_missing_user():
        repository = AsyncMock()
        repository.get_by_email_or_username.return_value = None
        service = AuthService(repository=repository)

        with pytest.raises(HTTPException) as exc_info:
            await service.login(LoginSchema(credential="ash", password="pikachu123"))

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert exc_info.value.detail == "Invalid credentials"

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_rejects_invalid_password(monkeypatch):
        user = SimpleNamespace(id=uuid4(), password="hashed")
        repository = AsyncMock()
        repository.get_by_email_or_username.return_value = user
        monkeypatch.setattr("app.domain.auth.service.verify_password", lambda *_: False)
        service = AuthService(repository=repository)

        with pytest.raises(HTTPException) as exc_info:
            await service.login(LoginSchema(credential="ash", password="bad-password"))

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        repository.update_auth_failure.assert_awaited_once_with(user.id)

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_returns_token_for_valid_user(monkeypatch):
        user = SimpleNamespace(id=uuid4(), password="hashed")
        repository = AsyncMock()
        repository.get_by_email_or_username.return_value = user
        monkeypatch.setattr("app.domain.auth.service.verify_password", lambda *_: True)
        monkeypatch.setattr(
            "app.domain.auth.service.create_access_token",
            lambda payload: f"token-{payload['sub']}",
        )
        service = AuthService(repository=repository)

        result = await service.login(
            LoginSchema(credential="ash", password="pikachu123")
        )

        assert result.access_token == f"token-{user.id}"
        assert result.token_type == "bearer"
        repository.update_auth_success.assert_awaited_once_with(user.id)
