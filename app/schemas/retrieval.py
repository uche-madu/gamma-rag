from typing import List
from pydantic import BaseModel, HttpUrl

class RetrievedArticle(BaseModel):
    stock_symbol: str | None = None
    title: str | None = None
    url: HttpUrl | None = None
    published_date: str | None = None
    content: str
    score: float | None = None

class RetrievalResponse(BaseModel):
    query: str
    retrieved_insights: List[RetrievedArticle]

class ErrorResponse(BaseModel):
    message: str
