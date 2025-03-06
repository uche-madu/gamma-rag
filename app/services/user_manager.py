import re
import uuid
import os

from fastapi import Depends, Request
from fastapi_users import (
    InvalidPasswordException, 
    BaseUserManager, 
    FastAPIUsers, 
    UUIDIDMixin, 
    models
) 
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from ..schemas.user import UserCreate
from ..database import get_async_session
from ..models import User

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "default_secret")

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET

    async def on_after_register(self, user: User, request: Request | None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    async def validate_password(
        self,
        password: str,
        user: UserCreate | User,
    ) -> None:
        if len(password) < 8:
            raise InvalidPasswordException (
                reason="Password should be at least 8 characters"
            )
        if user.email in password:
            raise InvalidPasswordException(
                reason="Password should not contain e-mail"
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise InvalidPasswordException(
                reason="Password must contain at least one special character"
            )


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=None)

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

async def get_user_manager(user_db=Depends(get_user_db)) -> UserManager:
    return UserManager(user_db, PasswordHelper())

auth_backend = AuthenticationBackend[User, uuid.UUID](
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)