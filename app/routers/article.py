from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
import langchain
import langgraph_sdk
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import Annotated

from ..database import get_async_session
from ..schemas.article import ArticleResponse, ArticleUpdateEmbedding
from ..services.article import embed_article, embed_articles
from ..models.article import Article
from ..services.retrieval import format_retrieved_articles
from ..schemas.retrieval import RetrievalResponse, ErrorResponse

router = APIRouter(prefix="/articles", tags=["Articles"])

@router.post("/{article_id}/embed", response_model=ArticleResponse)
async def process_embedding(
    article_id: int,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_async_session)]
):
    article = await session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.is_embedded:
        raise HTTPException(status_code=400, detail="Article already embedded")

    # Add the embedding task to background tasks
    background_tasks.add_task(embed_article, article_id, session)
    
    return ArticleResponse.model_validate(article)

@router.post("/embed-all", response_model=dict)
async def process_embeddings(
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_async_session)]
):
    """Trigger embedding for all unprocessed articles in the background."""
    
    # Add the embedding task to background tasks
    background_tasks.add_task(embed_articles, session)

    return {"message": "Embedding process started for all articles."}


# @router.get("/financial-advice/", response_model=RetrievalResponse | ErrorResponse)
# async def get_financial_advice(
#     query: str, 
#     session: AsyncSession = Depends(get_async_session)
#     ):
#     """Endpoint to fetch financial insights based on user queries."""
#     return await format_retrieved_articles(query)


