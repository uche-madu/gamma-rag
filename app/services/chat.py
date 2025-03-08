import asyncio
import re
from datetime import datetime
from typing import List, Sequence, Union, TypedDict
from typing_extensions import Annotated
import uuid
from textwrap import dedent

from langgraph.graph import StateGraph, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from langchain_core.runnables import RunnableLambda, RunnableConfig
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

    # Simple averaging for demonstration; adjust weights as needed
    combined_score = (vader_score + textblob_score) / 2

    if combined_score >= 0.05:
        return "positive"
    elif combined_score <= -0.05:
        return "negative"
    else:
        return "neutral"

def extract_user_response(response: str) -> str:
    """
    Extract the user-facing response by first removing any <think>...</think> tags 
    and then extracting the content between the first pair of '---' delimiters.
    
    Any text outside the delimiters is removed, as it is not meant for the user.
    If the delimiters are not found, the cleaned response (without think tags) is returned.
    """
    # Remove content within <think>...</think> tags.
    response_cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Extract the text between the first pair of triple-dash delimiters.
    match = re.search(r'---\s*(.*?)\s*---', response_cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return response_cleaned.strip()


# Create a RunnableLambda for the output parser
output_parser = RunnableLambda(extract_user_response)

# Get the current date dynamically
current_date = datetime.today().strftime("%B %d, %Y")

prompt_template = ChatPromptTemplate.from_messages([
    ("system", dedent(f"""\ 
        You are an experienced financial analyst specializing in investment research.
        Aside from that, you can have regular, non-investment conversations with the user.
        When the input is related to your primary task of investment research and financial advisory,
        try to retrieve relevant information to provide an informed response.

        Be flexible in how you present your analysis, avoiding a rigid structure.
        Ensure your response is clear, actionable, and personalized for the user.
        When you respond, address the user directly, without using third-person language.

        If the query is about investment advice, provide a summary of insights, discuss potential advantages
        and risks, and tailor your response to the sentiment captured from the user input.
        Include a disclaimer that this is not professional financial advice, and use recent information by default unless otherwise specified.
        If there's no relevant data, briefly mention that and suggest a different query or approach.

        Your response does not have to be too lengthy—be concise, friendly, and to the point.

        Today's date is {current_date}.
    """)),
    ("human", dedent("""\
        **Conversation History:**
        {conversation_history}

        **Retrieved Articles:**
        {formatted_articles}
    """))
])

# Initialize MemorySaver for checkpointing
memory = MemorySaver()

# Create a config with all required keys
thread_id = str(uuid.uuid4())
config: RunnableConfig = RunnableConfig(configurable={
    "thread_id": thread_id,
    "checkpoint_ns": "default_ns",
    "checkpoint_id": "default_id"
})

class GraphState(TypedDict):
    """State management for user queries, retrieved documents, and AI responses."""
    messages: Annotated[List, add_messages]
    retrieved_docs: Union[Sequence[Union[RetrievedArticle, dict]], str]
    formatted_query: str
    sentiment: str
    response: str
    thread_id: str  # added to satisfy checkpointer if needed


def serialize_retrieved_article(article: RetrievedArticle) -> dict:
    """
    Convert a RetrievedArticle pydantic model (from Pydantic v2) into a JSON-serializable dictionary.
    """
    data = article.model_dump()
    if "url" in data:
        data["url"] = str(data["url"])
    return data


async def process_query(state: GraphState) -> GraphState:
    """Retrieve relevant articles and update state with the new query."""
    # Get the new query from the last message (supporting both dicts and objects)
    last_message = state["messages"][-1]
    query = last_message["content"] if isinstance(last_message, dict) else last_message.content
    logger.info(f"Processing query: {query}")

    # Here we assume that state["messages"] is already our conversation history.
    # If not, you could initialize a dedicated 'conversation_history' key.
    # For this example, we'll treat state["messages"] as the full history.

    try:
        articles_response = await format_retrieved_articles(query)
        logger.info(f"Retrieved response type: {type(articles_response)}")

        if isinstance(articles_response, RetrievalResponse):
            articles = articles_response.retrieved_insights
            logger.info(f"Retrieved {len(articles)} articles.")
            if isinstance(articles, list):
                articles = [serialize_retrieved_article(a) for a in articles]
        elif isinstance(articles_response, ErrorResponse):
            articles = articles_response.message
            logger.warning(f"ErrorResponse received: {articles}")
        else:
            raise ValueError("Unexpected response format from format_retrieved_articles.")

        state["retrieved_docs"] = articles
        logger.info(f"Updated state['retrieved_docs']: {articles[:2] if isinstance(articles, list) else articles}")
    except Exception as e:
        logger.error(f"Error retrieving articles: {e}")
        state["retrieved_docs"] = "An error occurred while retrieving articles."

    return state


async def format_prompt(state: GraphState) -> GraphState:
    """Format prompt by combining conversation history and retrieved articles (or a fallback if none exist)."""
    logger.info("Formatting prompt...")
    logger.debug(f"Current retrieved_docs: {state['retrieved_docs']}")

    # Build conversation history from all messages.
    conversation_history = "\n".join(
        f"{msg['role']}: {msg['content']}" 
        if isinstance(msg, dict) 
        else f"human: {msg.content}"
        for msg in state["messages"]
    )

    # Format retrieved articles if available.
    if isinstance(state["retrieved_docs"], list) and state["retrieved_docs"]:
        formatted_articles = "\n\n".join(
            f"- **{article['title']}** (Published on {datetime.fromisoformat(article['published_date']).strftime('%B %d, %Y') if article.get('published_date') else 'Unknown date'}): "
            f"{article['content'][:200].strip()}... [Read more: {str(article['url'])}]"
            for article in state["retrieved_docs"]
        )
    else:
        # Fallback message: Inform the LLM that no recent articles were found.
        formatted_articles = (
            "No recent articles or data were retrieved for this topic. "
            "Respond briefly using any general market knowledge you have."
        )

    logger.debug(f"Formatted articles: {formatted_articles[:200]}")
    logger.debug(f"Conversation history: {conversation_history[:200]}")

    try:
        state["formatted_query"] = prompt_template.format(
            conversation_history=conversation_history,
            formatted_articles=formatted_articles
        )
        logger.info("Prompt formatted successfully.")
    except Exception as e:
        logger.error(f"Error formatting prompt: {e}")
        state["formatted_query"] = "Error formatting the query."

    return state


async def analyze_sentiment(state: GraphState) -> GraphState:
    """Analyze the sentiment of the user query and update the prompt."""
    logger.info("Analyzing sentiment for the query...")
    last_message = state["messages"][-1]
    message_text = last_message["content"] if isinstance(last_message, dict) else last_message.content
    sentiment = await asyncio.to_thread(get_combined_sentiment, message_text)
    state["sentiment"] = sentiment

    if sentiment == "positive":
        sentiment_prompt = (
            "The user appears optimistic about this investment. Provide a balanced analysis with potential opportunities and risks."
        )
    elif sentiment == "negative":
        sentiment_prompt = (
            "The user appears cautious about this investment. Focus on risk mitigation strategies and market stability."
        )
    else:
        sentiment_prompt = (
            "The user seems neutral about this investment. Provide an unbiased and comprehensive analysis."
        )

    state["formatted_query"] += "\n\n" + sentiment_prompt
    logger.debug(f"Sentiment analysis complete. Sentiment: {sentiment}")
    return state

async def generate_response(state: GraphState) -> GraphState:
    """Generate AI response and process output."""
    logger.info("Generating AI response...")
    logger.debug(f"Formatted Query (first 200 chars): {state['formatted_query'][:200]}")

    try:
        response = await groq_llm.ainvoke(state["formatted_query"], config=config)
        raw_response = response.content
        if isinstance(raw_response, str):
            state["response"] = await output_parser.ainvoke(raw_response, config=config)
        logger.info(f"Generated and processed response successfully. Length: {len(state['response'])}")
    except Exception as e:
        logger.error(f"Error generating or processing chat response: {e}")
        state["response"] = "Sorry, I encountered an issue processing your request."
    return state

async def rag_chat_workflow(query: str) -> dict:
    """
    Initialize, compile, and run the LangGraph workflow for the given query.
    Returns the final state produced by the workflow.
    """
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

    compiled_workflow = graph.compile(checkpointer=memory)
    
    initial_state = {
        "messages": [{"role": "user", "content": query}],
        "retrieved_docs": [],
        "formatted_query": "",
        "sentiment": "",
        "response": "",
        "thread_id": thread_id  # if needed
    }

    final_state = await compiled_workflow.ainvoke(initial_state, config=config)
    logger.info("LangGraph workflow execution completed.")
    return final_state
