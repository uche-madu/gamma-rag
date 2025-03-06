from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ArticleBase(BaseModel):
    url: str
    stock_symbol: str
    title: str | None = None
    author: str | None = None
    published_date: str | None = None
    content: str | None = None


class ArticleCreate(ArticleBase):
    pass


class ArticleResponse(ArticleBase):
    id: int
    is_embedded: bool
    scraped_at: datetime

    model_config = ConfigDict(
        from_attributes=True, 
        str_strip_whitespace=True
    )


class ArticleUpdateEmbedding(BaseModel):
    is_embedded: bool
