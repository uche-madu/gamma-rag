from loguru import logger
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends

from ..services.chat import rag_chat_workflow
from ..services.user_manager import current_active_user
from ..models import User
from ..schemas.chat import ChatRequest, ChatResponse 

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user: Annotated[User, Depends(current_active_user)]):
    """Endpoint to process user queries and generate AI responses
    based on the retrieved documents.
    """
    logger.info(f"Received chat request from user: {user.id}, query: {request.query}")
    
    try:
        logger.info("Initializing RAG chat workflow...")
        workflow = await rag_chat_workflow()
        
        initial_state = {
            "query": request.query,  # Extract query from request model
            "retrieved_docs": [],
            "formatted_query": "",
            "response": ""
        }
        
        logger.info(f"Starting workflow execution with initial state: {initial_state}")

        async for state in workflow.astream(initial_state):
            logger.debug(f"Workflow state updated: {state}")  # Log intermediate states
            final_state = state
    
        logger.success("Workflow execution completed successfully.")
        logger.info(f"Final response generated: {final_state["generate_response"]["response"]}")

        return ChatResponse(response=final_state["generate_response"]["response"])

    except Exception as e:
        logger.exception("Chat endpoint error")
        raise HTTPException(status_code=500, detail="Internal server error")
