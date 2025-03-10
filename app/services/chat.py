import asyncio
import re
from datetime import datetime
from typing import Literal, Sequence, Union
import uuid

from langgraph.graph import StateGraph, MessagesState, END
from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from langchain_core.runnables import RunnableLambda, RunnableConfig
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

from ..schemas.retrieval import ErrorResponse, RetrievalResponse, RetrievedArticle
from .retrieval import format_retrieved_articles
from ..config import ds_r1_llama_70b_llm, llama3_70b_llm

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
    response_cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    match = re.search(r'---\s*(.*?)\s*---', response_cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return response_cleaned.strip()

def serialize_retrieved_article(article: RetrievedArticle) -> dict:
    """
    Convert a RetrievedArticle pydantic model (from Pydantic v2) into a JSON-serializable dictionary.
    """
    data = article.model_dump()
    if "url" in data:
        data["url"] = str(data["url"])
    return data

# Create a RunnableLambda for the output parser
output_parser = RunnableLambda(extract_user_response)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", """
        You are an experienced financial analyst specializing in investment research.
        Conversation Summary: {conversation_summary}
        
        **Retrieved Articles:**
        {formatted_articles}
        
        You are designed to provide detailed analysis and balanced recommendations based on recent news articles retrieved from a vectorstore.
        When the query is investment-related, use the retrieved articles to deliver a comprehensive analysis covering potential opportunities, risks, and market trends. If no relevant data is retrieved, inform the user and suggest a refined query.
        If the user's query is casual or not directly related to investments or finance, respond with a variation of depending on the context:
            "This system is optimized for handling finance and investment-related queries. Please ask a question related to investments or financial markets for a comprehensive analysis."
        Ensure your response is clear, actionable, and personalized. Address the user directly without using third-person language.
        Conditionally (only for suitable queries) include a disclaimer. Use recent information by default unless otherwise specified. When using retrieved articles, include the unique source urls for reference at the end of the response.
        
        Today's date is {current_date}.
    """),
    ("human", """
        {query}
    """)
])

# Initialize MemorySaver for checkpointing
memory = MemorySaver()

# Create a config with all required keys
thread_id = str(uuid.uuid4())
config: RunnableConfig = RunnableConfig(configurable={"thread_id": thread_id })

# Extend State from MessagesState to include a summary.
class State(MessagesState):
    """State management for user queries, retrieved documents, and AI responses."""
    retrieved_docs: Union[Sequence[Union[RetrievedArticle, dict]], str]
    formatted_query: str
    sentiment: str
    summary: str

# Node: Process query (retrieve articles).
async def process_query(state: State) -> State:
    last_message = state["messages"][-1]
    query = last_message["content"] if isinstance(last_message, dict) else last_message.content
    logger.info(f"Processing query: {query}")
    try:
        if not isinstance(query, str):
            raise ValueError("Query must be a string.")
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
        return state
    except Exception as e:
        logger.error(f"Error retrieving articles: {e}")
        raise e


# Node: Format prompt using conversation history (including summary if available).
async def format_prompt(state: State) -> State:
    logger.info("Formatting prompt...")

    if isinstance(state["retrieved_docs"], list) and state["retrieved_docs"]:
        formatted_articles = "\n\n".join(
            f"- **{article['title']}** (Published on {datetime.fromisoformat(article['published_date']).strftime('%B %d, %Y') if article.get('published_date') else 'Unknown date'}): "
            f"{article['content'][:200].strip()}... [Read more: {str(article['url'])}]"
            for article in state["retrieved_docs"]
        )
    else:
        formatted_articles = (
            "No recent articles or data were retrieved for this topic. "
        )
    try:
        current_date = datetime.today().strftime("%B %d, %Y")
        conversation_summary = state.get("summary", "")
        state["formatted_query"] = prompt_template.format(
            conversation_summary=conversation_summary,
            formatted_articles=formatted_articles,
            current_date=current_date,
            query=state["messages"][-1].content
        )
        logger.info("Prompt formatted successfully.")
        return state
    except Exception as e:
        logger.error(f"Error formatting prompt: {e}")
        raise e

# Node: Analyze sentiment.
async def analyze_sentiment(state: State) -> State:
    logger.info("Analyzing sentiment for the query...")
    last_message = state["messages"][-1]
    message_text = last_message["content"] if isinstance(last_message, dict) else last_message.content
    sentiment = await asyncio.to_thread(get_combined_sentiment, message_text)
    state["sentiment"] = sentiment
    if sentiment == "positive":
        sentiment_prompt = (
            "The user appears optimistic. Provide a balanced analysis with potential opportunities and risks if the query is related to investment or finance."
        )
    elif sentiment == "negative":
        sentiment_prompt = (
            "The user appears cautious. Focus on risk mitigation strategies and market stability if the query is related to investment or finance."
        )
    else:
        sentiment_prompt = (
            "The user seems neutral. Provide an unbiased and comprehensive analysis if the query is related to investment or finance."
        )
    state["formatted_query"] += "\n\n" + sentiment_prompt
    logger.debug(f"Sentiment analysis complete. Sentiment: {sentiment}")
    return state

# Node: Generate response.
async def generate_response(state: State):
    logger.info("Generating AI response...")
    logger.debug(f"Formatted Query (first 200 chars): {state['formatted_query'][:200]}")
    try:
        response = await ds_r1_llama_70b_llm.ainvoke(state["formatted_query"], config=config)
        raw_response = response.content
        if isinstance(raw_response, str):
            response = await output_parser.ainvoke(raw_response, config=config)
            logger.info(f"Generated and processed response successfully. Length: {len(state['messages'])}")
            return {"messages": [response]}
    except Exception as e:
        logger.error(f"Error generating or processing chat response: {e}")
        raise e

# Node: Summarize conversation history using llama3_70b_llm.
async def summarize_conversation(state: State):
    logger.info("Summarizing conversation history...")
    summary = state.get("summary", "")
    if summary:
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
    else:
        summary_message = "Create a summary of the conversation above:"
    
    # Create a summarization prompt by appending the summary instruction.
    messages_for_summary = state["messages"] + [HumanMessage(content=summary_message)]
    
    try:
        response = await llama3_70b_llm.ainvoke(messages_for_summary, config=config)
        logger.info("Conversation history summarized.")
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
        return {"summary": response.content, "messages": delete_messages}

    except Exception as e:
        logger.error(f"Error summarizing conversation: {e}")
        raise e

# Conditional node: Decide whether to summarize the conversation.
async def should_continue(state: State) -> Literal["summarize_conversation", END]:
    if len(state["messages"]) > 6:
        return "summarize_conversation"
    return END

# Workflow: Chain nodes including the conditional summarization.
# Conditional node: Decide whether to summarize the conversation.
async def rag_chat_workflow(query: str) -> str:
    graph = StateGraph(State)
    
    # Add nodes.
    graph.add_node("process_query", process_query)
    graph.add_node("format_prompt", format_prompt)
    graph.add_node("analyze_sentiment", analyze_sentiment)
    graph.add_node("generate_response", generate_response)
    graph.add_node("summarize_conversation", summarize_conversation)
    
    # Set entry point.
    graph.set_entry_point("process_query")
    # Define edges.
    graph.add_edge("process_query", "format_prompt")
    graph.add_edge("format_prompt", "analyze_sentiment")
    graph.add_edge("analyze_sentiment", "generate_response")
    
    # Add a conditional edge from generate_response.
    graph.add_conditional_edges("generate_response", should_continue)
    # After summarization, end the workflow.
    graph.add_edge("summarize_conversation", END)
    
    logger.info("LangGraph workflow initialized.")
    compiled_workflow = graph.compile(checkpointer=memory)

    # Generate the PNG data.
    png_data = compiled_workflow.get_graph().draw_mermaid_png()
    with open("assets/state_graph.png", "wb") as f:
        f.write(png_data)
    logger.info("State graph saved to state_graph.png")
    
    input_message = HumanMessage(content=query)
    final_state = await compiled_workflow.ainvoke({"messages": [input_message]}, config=config)
    
    # Extract the final response from the last message.
    if final_state.get("messages"):
        final_response = final_state["messages"][-1].content
        logger.success("Workflow execution completed successfully.")
        logger.info(f"Final response: {final_response}")
        return final_response
    else:
        logger.error("No messages found in final state.")
        return ""

