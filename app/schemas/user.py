from datetime import datetime, timezone
from typing import Optional
import uuid
from typing_extensions import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate



class UserRead(BaseUser[uuid.UUID]):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    is_verified: Optional[bool] = None


class UserCreate(BaseUserCreate):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC creation timestamp")
    is_verified: Optional[bool] = None


class UserUpdate(BaseUserUpdate):
    is_verified: Optional[bool] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserInDB(UserResponse):
    hashed_password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8)]


