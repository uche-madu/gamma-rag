from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.chat import rag_chat_workflow
from ..database import get_async_session
from ..services.websocket_auth import ConnectionManager, get_user_from_token

manager = ConnectionManager()
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Authenticated WebSocket for real-time AI chat with streaming responses."""
    user = await get_user_from_token(token, session)
    if not user:
        await websocket.close(code=1008)  # Policy Violation
        return

    user_id = user.id
    await manager.connect(websocket, user_id)
    logger.info(f"✅ WebSocket connected: User {user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query")
            if not query:
                await manager.send_personal_message("❌ Query cannot be empty", user_id)
                continue

            logger.info(f"📩 Received query from User {user_id}: {query}")
            final_state = await rag_chat_workflow(query)
            response_text = final_state.get("response", "")
            if response_text:
                await manager.send_personal_message(response_text, user_id)

            await manager.broadcast(f"🔔 User {user_id} sent a query", exclude_user_id=user_id)

    except WebSocketDisconnect:
        logger.warning(f"⚠️ User {user_id} disconnected.")
        manager.disconnect(user_id)
        await manager.broadcast(f"🔴 User {user_id} left the chat")

    except Exception as e:
        logger.error(f"❌ WebSocket error for User {user_id}: {e}")
        await websocket.send_json({"error": "Internal server error"})
        await websocket.close()

    finally:
        manager.disconnect(user_id)
        logger.info(f"🔴 WebSocket closed for User {user_id}")
