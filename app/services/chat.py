
import datetime
from typing import List, Dict, TypedDict, Union, Sequence

from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from ..schemas.retrieval import ErrorResponse, RetrievalResponse, RetrievedArticle

from .retrieval import format_retrieved_articles
from ..config import groq_llm


# Get the current date dynamically
current_date = datetime.datetime.today().strftime("%B %d, %Y")

# Define prompt template
prompt_template = ChatPromptTemplate.from_messages([
    ("system",
        "You are an experienced financial analyst specializing in investment research. "
        "Your task is to analyze relevant stock market insights based on retrieved data. "
        "Ensure your response is data-driven, structured, and easy to understand."
    ),
    ("human",
        "Today's date is {current_date}.\n\n"
        "Consider the user's sentiment toward this investment.\n"
        "### Retrieved Financial Articles:\n"
        "{formatted_articles}\n\n"
        "Based on the above, analyze the company's current market position and provide an investment assessment.\n\n"
        "### Response Format:\n"
        "1. **Summary of Key Financial Insights:**\n"
        "2. **Advantages of Investing:**\n"
        "3. **Risks and Disadvantages:**\n"
        "4. **Sentiment-Based Recommendation:**\n\n"
        "Ensure your response is professional, structured, and actionable."
    ),
])

# Define state management for the LangGraph workflow
# I want to also manage memory in the workflow via langgraph

class GraphState(TypedDict):
    """State management for user queries, retrieved documents, and AI responses."""
    query: str
    retrieved_docs: Union[List[RetrievedArticle], str]
    formatted_query: str
    response: str


async def process_query(state: GraphState) -> GraphState:
    """Retrieve relevant articles and update state."""
    query = state["query"]
    logger.info(f"Processing query: {query}")

    try:
        articles_response = await format_retrieved_articles(query)
        logger.info(f"Retrieved response type: {type(articles_response)}")

        if isinstance(articles_response, RetrievalResponse):
            articles = articles_response.retrieved_insights
            logger.info(f"Retrieved {len(articles)} articles.")
        elif isinstance(articles_response, ErrorResponse):
            articles = articles_response.message
            logger.warning(f"ErrorResponse received: {articles}")
        else:
            raise ValueError("Unexpected response format from format_retrieved_articles.")

        state["retrieved_docs"] = articles
        logger.info(f"Updated state['retrieved_docs']: {articles[:2]}")  # Log first 2 for brevity

    except Exception as e:
        logger.error(f"Error retrieving articles: {e}")
        state["retrieved_docs"] = "An error occurred while retrieving articles."

    return state


async def format_prompt(state: GraphState) -> GraphState:
    """Format prompt with retrieved docs."""
    logger.info("Formatting prompt...")
    logger.debug(f"Current retrieved_docs: {state['retrieved_docs']}")

    try:
        state["formatted_query"] = prompt_template.format(
            current_date=current_date,
            formatted_articles=state["retrieved_docs"]
        )
        logger.info("Prompt formatted successfully.")
    except Exception as e:
        logger.error(f"Error formatting prompt: {e}")
        state["formatted_query"] = "Error formatting the query."

    return state

async def generate_response(state: GraphState) -> GraphState:
    """Generate AI response."""
    logger.info("Generating AI response...")
    logger.debug(f"Formatted Query: {state['formatted_query'][:200]}")  # Log first 200 chars

    try:
        response_chunks = [chunk.content async for chunk in groq_llm.astream(state["formatted_query"]) if isinstance(chunk.content, str)]
        state["response"] = "".join(response_chunks)
        logger.info(f"Generated response successfully. Length: {len(state['response'])}")
    except Exception as e:
        logger.error(f"Error generating chat response: {e}")
        state["response"] = "Sorry, I encountered an issue processing your request."

    return state

async def rag_chat_workflow():
    """Initialize LangGraph workflow."""
    graph = StateGraph(GraphState)
    
    graph.add_node("process_query", process_query)
    graph.add_node("format_prompt", format_prompt)
    graph.add_node("generate_response", generate_response)
    
    graph.set_entry_point("process_query")
    graph.add_edge("process_query", "format_prompt")
    graph.add_edge("format_prompt", "generate_response")

    logger.info("LangGraph workflow initialized.")
    
    return graph.compile()



