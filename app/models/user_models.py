from datetime import datetime, timezone
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import TIMESTAMP, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class User(SQLAlchemyBaseUserTableUUID, Base): 

    username: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(type_=TIMESTAMP(timezone=True), nullable=False)
    is_verified: bool = False

