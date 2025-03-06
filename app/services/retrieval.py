from typing import List

from loguru import logger
from langchain_community.vectorstores import SupabaseVectorStore

from app.schemas.retrieval import ErrorResponse, RetrievalResponse, RetrievedArticle
from ..config import supabase, embedding_model


# Initialize vector store
vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=embedding_model,
    table_name="documents",
    query_name="match_documents",
)

async def retrieve_relevant_articles(query: str) -> List[RetrievedArticle]:
    """Retrieve top-k most relevant stock-related articles based on user query."""
    try:
        logger.info(f"Searching for relevant articles related to: {query}")

        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
 
        results = await retriever.ainvoke(query)

        if not results:
            logger.warning("No relevant articles found.")
            return []

        logger.info(f"Found {len(results)} relevant articles.")

        retrieved_articles = []
        for doc in results:
            metadata = doc.metadata
            retrieved_articles.append(
                RetrievedArticle(
                    stock_symbol=metadata.get("stock_symbol"),
                    title=metadata.get("title"),
                    url=metadata.get("url"),
                    published_date=metadata.get("published_date"),
                    content=doc.page_content,
                )
            )

        logger.debug(f"Formatted retrieved articles: {[article.model_dump() for article in retrieved_articles]}")


        return [article.model_dump() for article in retrieved_articles]

    except Exception as e:
        logger.exception(f"Error retrieving articles: {e}")
        return []


async def format_retrieved_articles(query: str) -> RetrievalResponse | ErrorResponse:
    """Retrieve relevant articles and return a structured response."""
    retrieved_docs = await retrieve_relevant_articles(query)

    if not retrieved_docs:
        return ErrorResponse(message="No relevant financial insights found for your query.")

    return RetrievalResponse(query=query, retrieved_insights=retrieved_docs)
