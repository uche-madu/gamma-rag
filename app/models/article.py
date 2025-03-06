from datetime import datetime
from sqlalchemy import Text, String, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    stock_symbol: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_embedded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
