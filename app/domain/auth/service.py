from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException

from app.core.exceptions import handle_service_exception
from app.core.security import create_access_token, get_password_hash, verify_password
from app.domain.auth.schema import (
    AuthResponseSchema,
    LoginResponseSchema,
    LoginSchema,
    RegisterSchema,
)
from app.domain.auth.repository import UserRepository
from app.models.enums import StatusEnum
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        trainer_repository=None,
    ) -> None:
        self.repository = repository
        self.trainer_repository = trainer_repository

    async def register(self, data: RegisterSchema) -> User:
        try:
            existing_email = await self.repository.get_by_email(data.email)
            if existing_email:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="Email already registered",
                )

            existing_username = await self.repository.get_by_username(data.username)
            if existing_username:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="Username already taken",
                )

            user_data = data.model_dump()
            user_data["password"] = get_password_hash(data.password)
            user_data["status"] = StatusEnum.ACTIVE

            return await self.repository.create(user_data)

        except Exception as exception:
            handle_service_exception(
                exception,
                logger=logger,
                service="AuthService",
                operation="register",
                raise_exception=True,
            )

    async def login(self, data: LoginSchema) -> LoginResponseSchema:
        try:
            user = await self.repository.get_by_email_or_username(data.credential)

            if not user:
                raise HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            if not verify_password(data.password, user.password):
                await self.repository.update_auth_failure(user.id)
                raise HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            await self.repository.update_auth_success(user.id)
            token = create_access_token({"sub": str(user.id)})

            return LoginResponseSchema(access_token=token)

        except Exception as exception:
            handle_service_exception(
                exception,
                logger=logger,
                service="AuthService",
                operation="login",
                raise_exception=True,
            )

    async def me(self, current_user: User) -> AuthResponseSchema:
        trainer = None
        if self.trainer_repository:
            trainer = await self.trainer_repository.get_by_user_id(current_user.id)
            if trainer is not None and not isinstance(
                getattr(trainer, "id", None), UUID
            ):
                trainer = None

        return AuthResponseSchema(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            status=current_user.status,
            username=current_user.username,
            created_at=current_user.created_at,
            updated_at=getattr(current_user, "updated_at", None),
            deleted_at=getattr(current_user, "deleted_at", None),
            total_authentications=getattr(current_user, "total_authentications", None),
            authentication_success=getattr(
                current_user, "authentication_success", None
            ),
            authentication_failures=getattr(
                current_user, "authentication_failures", None
            ),
            last_authentication_at=getattr(
                current_user, "last_authentication_at", None
            ),
            trainer=trainer,
        )
