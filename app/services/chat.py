import asyncio
import re
import datetime
from typing import List, Dict, TypedDict, Union, Sequence
import uuid

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from langchain_core.runnables import RunnableLambda
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

from ..schemas.retrieval import ErrorResponse, RetrievalResponse, RetrievedArticle
from .retrieval import format_retrieved_articles
from ..config import groq_llm

def get_combined_sentiment(text: str) -> str:
    # VADER sentiment score
    analyzer = SentimentIntensityAnalyzer()
    vader_score = analyzer.polarity_scores(text)['compound']
    
    # TextBlob sentiment polarity
    textblob_score = TextBlob(text).sentiment.polarity  # type: ignore

    combined_score = (vader_score + textblob_score) / 2
    if combined_score >= 0.05:
        return "positive"
    elif combined_score <= -0.05:
        return "negative"
    else:
        return "neutral"

def extract_company_name(query: str) -> str:
    """Extracts a company name from the query if clearly specified.
       Returns an empty string if the query appears general."""
    # Basic extraction using regex; tweak as needed.
    match = re.search(r'\b(?:about|regarding|for|with respect to)?\s*([\w\s&\.\-]+)\s*\(?[A-Z]{1,5}\)?', query, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        invalid_keywords = {"market", "trends", "stock", "investment", "price", "economy"}
        if extracted.lower() in invalid_keywords:
            return ""
        return extracted
    return ""

# Define the custom output parser function
def remove_think_tags(response: str) -> str:
    """
    Remove content within <think></think> tags and strip out chain-of-thought language
    from the model's response.
    """
    # Remove any <think></think> tags
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Remove chain-of-thought or internal reasoning markers.
    # This regex removes phrases like "based on the thought process:" or "chain of thought:"
    response = re.sub(r'(?i)(based on the thought process:?.*?)(?=\n---)', '', response, flags=re.DOTALL)
    response = re.sub(r'(?i)(chain of thought:?.*?)(?=\n---)', '', response, flags=re.DOTALL)
    
    # Optionally, remove any remaining internal markers if needed (adjust regex as necessary)
    # For example, remove any sentences starting with "Internal:" or similar:
    response = re.sub(r'(?i)^internal:.*$', '', response, flags=re.MULTILINE)
    
    return response.strip()

output_parser = RunnableLambda(remove_think_tags)

current_date = datetime.datetime.today().strftime("%B %d, %Y")

# Updated prompt template without forcing company-specific language
prompt_template = ChatPromptTemplate.from_messages([
    ("system",
        "You are an experienced financial analyst specializing in market research. "
        "Your task is to analyze stock market insights based on the retrieved data. "
        "Provide a concise, clear, and actionable analysis. "
        "If the query is company-specific, include analysis of that company's market position; "
        "if the query is general, focus on overall market trends. "
        "If there's no relevant data, mention that and suggest checking additional sources."
    ),
    ("human",
        "Today's date is {current_date}.\n\n"
        "Retrieved Financial Articles:\n"
        "{formatted_articles}\n\n"
        "{additional_instructions}"
    ),
])

memory = MemorySaver()
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

class GraphState(TypedDict):
    query: str
    retrieved_docs: Union[List[RetrievedArticle], str]
    formatted_query: str
    sentiment: str
    response: str

async def process_query(state: GraphState) -> GraphState:
    query = state["query"]
    logger.info(f"Processing query: {query}")
    try:
        articles_response = await format_retrieved_articles(query)
        logger.info(f"Retrieved response type: {type(articles_response)}")
        if isinstance(articles_response, RetrievalResponse) and articles_response.retrieved_insights:
            articles = articles_response.retrieved_insights
            logger.info(f"Retrieved {len(articles)} articles.")
        elif isinstance(articles_response, ErrorResponse):
            articles = articles_response.message
            logger.warning(f"ErrorResponse received: {articles}")
        else:
            articles = "No relevant financial insights found for your query."
        state["retrieved_docs"] = articles
        logger.info(f"Updated state['retrieved_docs']: {str(articles)[:100]}")
    except Exception as e:
        logger.error(f"Error retrieving articles: {e}")
        state["retrieved_docs"] = "An error occurred while retrieving articles."
    return state

async def format_prompt(state: GraphState) -> GraphState:
    logger.info("Formatting prompt...")
    query = state["query"].strip()
    
    # Check if query contains general market keywords.
    general_keywords = {"market", "trend", "economy", "global"}
    if any(kw in query.lower() for kw in general_keywords):
        company_section = ""
    else:
        company_name = await asyncio.to_thread(extract_company_name, query)
        company_section = f"Your query is related to {company_name}." if company_name else ""
    
    additional_instructions = ""
    if company_section:
        additional_instructions = company_section + " Ensure your analysis includes the company's market position."
    else:
        additional_instructions = "Provide a general market analysis and investment recommendation."
    
    if not state["retrieved_docs"] or state["retrieved_docs"] == "No relevant financial insights found for your query.":
        state["formatted_query"] = (
            f"Today's date is {current_date}.\n\n"
            f"I couldn't find recent financial insights for your query. {additional_instructions} "
            "Please check official sources for more details."
        )
        return state

    try:
        state["formatted_query"] = prompt_template.format(
            current_date=current_date,
            formatted_articles=state["retrieved_docs"],
            additional_instructions=additional_instructions
        )
        logger.info("Prompt formatted successfully.")
    except Exception as e:
        logger.error(f"Error formatting prompt: {e}")
        state["formatted_query"] = "Error formatting the query."
    return state

async def analyze_sentiment(state: GraphState) -> GraphState:
    logger.info("Analyzing sentiment for the query...")
    sentiment = await asyncio.to_thread(get_combined_sentiment, state["query"])
    state["sentiment"] = sentiment
    if sentiment == "positive":
        sentiment_prompt = "The user appears optimistic. Provide a balanced analysis with opportunities and risks."
    elif sentiment == "negative":
        sentiment_prompt = "The user appears cautious. Focus on risk mitigation and market stability."
    else:
        sentiment_prompt = "The user seems neutral. Provide an unbiased and succinct analysis."
    state["formatted_query"] += "\n\n" + sentiment_prompt
    logger.debug(f"Sentiment analysis complete. Sentiment: {sentiment}")
    return state

async def generate_response(state: GraphState) -> GraphState:
    logger.info("Generating AI response...")
    logger.debug(f"Formatted Query (first 200 chars): {state['formatted_query'][:200]}")
    try:
        response_chunks = [
            chunk.content async for chunk in groq_llm.astream(state["formatted_query"], config=config) # type: ignore
            if isinstance(chunk.content, str)
        ]
        raw_response = "".join(response_chunks)
        state["response"] = await output_parser.ainvoke(raw_response)
        logger.info(f"Generated response successfully. Length: {len(state['response'])}")
    except Exception as e:
        logger.error(f"Error generating or processing chat response: {e}")
        state["response"] = "Sorry, I encountered an issue processing your request."
    return state

async def rag_chat_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("process_query", process_query)
    graph.add_node("format_prompt", format_prompt)
    graph.add_node("analyze_sentiment", analyze_sentiment)
    graph.add_node("generate_response", generate_response)
    graph.set_entry_point("process_query")
    graph.add_edge("process_query", "format_prompt")
    graph.add_edge("format_prompt", "analyze_sentiment")
    graph.add_edge("analyze_sentiment", "generate_response")
    logger.info("LangGraph workflow initialized.")
    return graph.compile(checkpointer=memory)
