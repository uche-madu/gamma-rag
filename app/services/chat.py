import asyncio
import re
import datetime
from typing import List, Dict, TypedDict, Union, Sequence

from langgraph.graph import StateGraph
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
    textblob_score = TextBlob(text).sentiment.polarity

    # Simple averaging for demonstration; adjust weights as needed
    combined_score = (vader_score + textblob_score) / 2

    if combined_score >= 0.05:
        return "positive"
    elif combined_score <= -0.05:
        return "negative"
    else:
        return "neutral"


# Define the custom output parser function
def remove_think_tags(response: str) -> str:
    """
    Remove content within <think></think> tags from the model's response.
    """
    # Regular expression to match content within <think></think> tags
    think_tag_pattern = r'<think>.*?</think>'
    cleaned_response = re.sub(think_tag_pattern, '', response, flags=re.DOTALL)
    return cleaned_response.strip()

# Create a RunnableLambda for the output parser
output_parser = RunnableLambda(remove_think_tags)

# Get the current date dynamically
current_date = datetime.datetime.today().strftime("%B %d, %Y")

# Define prompt template
prompt_template = ChatPromptTemplate.from_messages([
    ("system",
        "You are an experienced financial analyst specializing in investment research. "
        "Your task is to analyze relevant stock market insights based on retrieved data. "
        "Be flexible in how you present your analysis, avoiding a rigid structure. "
        "Ensure your response is clear, actionable, and personalized for the user. "
        "When you respond, address the user directly, without using third-person language. "
        "You may provide a summary of insights, discuss potential advantages and risks, and offer a sentiment-based recommendation. "
        "Please provide your analysis and recommendation based on the retrieved information. If there's no relevant data, "
        "you can mention that and suggest a different query."
    ),
    ("human",
        "Today's date is {current_date}.\n\n"
        "Consider your sentiment towards this investment based on the following data.\n"
        "### Retrieved Financial Articles:\n"
        "{formatted_articles}\n\n"
        "Based on the retrieved information, provide an analysis of the company's market position "
        "and offer an investment recommendation.\n\n"
        "Feel free to vary the format and structure of your response, but ensure it is personalized, clear, "
        "and actionable. You may provide a summary of insights, discuss potential advantages and risks, and offer a sentiment-based recommendation."
    ),
])


class GraphState(TypedDict):
    """State management for user queries, retrieved documents, and AI responses."""
    query: str
    retrieved_docs: Union[List[RetrievedArticle], str]
    formatted_query: str
    sentiment: str
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

    if not state["retrieved_docs"]:
        state["formatted_query"] = (
            f"Today's date is {current_date}.\n\n"
            "No relevant financial insights were found for the given query. "
            "Please ask about stocks we have data on, such as Nvidia, Tesla, or Google."
        )
        return state

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

async def analyze_sentiment(state: GraphState) -> GraphState:
    """Analyze the sentiment of the user query and update the prompt."""
    logger.info("Analyzing sentiment for the query...")
    
    # Run sentiment analysis in a separate thread
    sentiment = await asyncio.to_thread(get_combined_sentiment, state["query"])
    state["sentiment"] = sentiment

    if sentiment == "positive":
        sentiment_prompt = "The user appears optimistic about this investment. Provide a balanced analysis with potential opportunities and risks."
    elif sentiment == "negative":
        sentiment_prompt = "The user appears cautious about this investment. Focus on risk mitigation strategies and market stability."
    else:
        sentiment_prompt = "The user seems neutral about this investment. Provide an unbiased and comprehensive analysis."

    # Append the sentiment-specific guidance to the formatted query
    state["formatted_query"] += "\n\n" + sentiment_prompt
    logger.debug(f"Sentiment analysis complete. Sentiment: {sentiment}")
    
    return state

async def generate_response(state: GraphState) -> GraphState:
    """Generate AI response and process output."""
    logger.info("Generating AI response...")
    logger.debug(f"Formatted Query: {state['formatted_query'][:200]}")  # Log first 200 chars

    try:
        # Stream response from the LLM
        response_chunks = [
            chunk.content async for chunk in groq_llm.astream(state["formatted_query"])
            if isinstance(chunk.content, str)
        ]
        raw_response = "".join(response_chunks)

        # Process the raw response to remove <think></think> tags
        state["response"] = await output_parser.ainvoke(raw_response)
        logger.info(f"Generated and processed response successfully. Length: {len(state['response'])}")
    except Exception as e:
        logger.error(f"Error generating or processing chat response: {e}")
        state["response"] = "Sorry, I encountered an issue processing your request."

    return state


async def rag_chat_workflow():
    """Initialize LangGraph workflow."""
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
    
    return graph.compile()

