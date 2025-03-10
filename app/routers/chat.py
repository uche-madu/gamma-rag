from loguru import logger
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends

from ..services.chat import rag_chat_workflow
from ..services.user_manager import current_active_user
from ..models import User
from ..schemas.chat import ChatRequest, ChatResponse 

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
# async def chat_endpoint(request: ChatRequest, user: Annotated[User, Depends(current_active_user)]):
    """Endpoint to process user queries and generate AI responses
    based on the retrieved documents.
    """
    logger.info(f"Received chat request, query: {request.query}")
    # logger.info(f"Received chat request from user: {user.id}, query: {request.query}")
    
    logger.info(f"Received chat request, query: {request.query}")
    try:
        logger.info("Running chat workflow...")
        response = await rag_chat_workflow(request.query)
        logger.info(f"Final response generated: {response}")
        return ChatResponse(response=response)
    except Exception as e:
        logger.exception("Chat endpoint error")
        raise HTTPException(status_code=500, detail="Internal server error")
