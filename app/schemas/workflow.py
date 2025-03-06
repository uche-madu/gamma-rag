from pydantic import BaseModel
from typing import List

class WorkflowState(BaseModel):
    """Tracks state throughout the LangGraph workflow."""
    user_query: str
    retrieved_articles: List[dict] | None = None
    sentiment: str | None = None
    generated_response: str | None = None
    structured_advice: dict | None = None
