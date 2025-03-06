import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger

from ..models.article import Article
from ..config import supabase, embedding_model


# Initialize vector store once
vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=embedding_model,
    table_name="documents",
    query_name="match_documents",
)


async def load_articles(session: AsyncSession) -> tuple[list[Document], list[Article]]:
    """Retrieve articles from DB, chunk content, and convert them to LangChain Documents."""
    
    result = await session.execute(select(Article).filter_by(is_embedded=False))
    articles = list(result.scalars().all())

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )

    documents: list[Document] = []
    for article in articles:
        if not article.content:
            continue

        if article.content:
            chunks = text_splitter.split_text(article.content)
        else:
            logger.warning(f"Article {article.id} has no content to embed.")
            return [], []

        for i, chunk in enumerate(chunks):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "id": article.id,
                        "url": article.url,
                        "stock_symbol": article.stock_symbol,
                        "title": article.title,
                        "author": article.author,
                        "published_date": article.published_date,
                        "chunk_id": i,
                    },
                )
            )

    logger.info(f"Loaded {len(documents)} document chunks for embedding.")
    return documents, articles



async def embed_articles(session: AsyncSession):
    """Embed chunked articles and store them in a vector database."""
    documents, articles = await load_articles(session)

    if not documents:
        logger.info("No new articles to embed.")
        return

    try:
        # Add documents without overwriting existing ones
        vector_store.add_documents(documents=list(documents)) 
        logger.success(f"Embedded {len(documents)} chunks into vector DB.")

        # Mark articles as embedded after successful storage
        for article in articles:
            article.is_embedded = True
        await session.commit()

    except Exception as e:
        logger.error(f"Failed to embed articles: {e}")


async def embed_article(article_id: int, session: AsyncSession):
    """Embed a single article asynchronously."""
    await asyncio.sleep(2)

    result = await session.execute(select(Article).filter(Article.id == article_id))
    article = result.scalars().first()

    if not article or article.is_embedded:
        logger.info(f"Article {article_id} already embedded or not found.")
        return

    # Process embedding for this article
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

    if article.content:
        chunks = text_splitter.split_text(article.content)

    documents = [
        Document(
            page_content=chunk,
            metadata={
                "id": article.id,
                "url": article.url,
                "stock_symbol": article.stock_symbol,
                "title": article.title,
                "author": article.author,
                "published_date": article.published_date,
                "chunk_id": i,
            },
        )
        for i, chunk in enumerate(chunks)
    ]

    try:
        vector_store.add_documents(documents)
        article.is_embedded = True
        await session.commit()
        logger.success(f"Embedded article {article_id} successfully.")

    except Exception as e:
        logger.error(f"Error embedding article {article_id}: {e}")
