from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from ..services.chat import rag_chat_workflow
from ..services.user_manager import get_user_manager, JWT_SECRET
from ..database import get_async_session
from ..models import User

class ConnectionManager:
    """Manages WebSocket connections and messaging."""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # Use str(UUID) for keys

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Accept WebSocket connection and store it."""
        await websocket.accept()
        self.active_connections[str(user_id)] = websocket

    def disconnect(self, user_id: UUID):
        """Remove user from active connections."""
        user_id_str = str(user_id)
        if user_id_str in self.active_connections:
            del self.active_connections[user_id_str]

    async def send_personal_message(self, message: str, user_id: UUID):
        """Send a direct message to a specific user."""
        websocket = self.active_connections.get(str(user_id))
        if websocket:
            await websocket.send_json({"response": message})

    async def broadcast(self, message: str, exclude_user_id: Optional[UUID] = None):
        """Send a message to all connected clients except the sender."""
        for uid, connection in self.active_connections.items():
            if exclude_user_id and uid == str(exclude_user_id):
                continue
            await connection.send_json({"broadcast": message})

manager = ConnectionManager()
router = APIRouter(prefix="/chat", tags=["Chat"])

async def get_user_from_token(token: str, session: AsyncSession) -> Optional[User]:
    """Authenticate user by decoding the JWT token and fetching user from DB."""
    try:
        logger.info(f"🔐 Authenticating WebSocket user with token: {token}")
        # Decode the token using the same secret and algorithm used in FastAPI Users.
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload: no subject found")

        user_id = UUID(user_id)

        # Fetch user from the database using the user manager.
        async with session.begin():
            user_manager_instance = await get_user_manager(session)
            user = await user_manager_instance.get(user_id)

        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        return user

    except JWTError as e:
        logger.warning(f"❌ JWT decode error: {e}")
        return None
    except Exception as e:
        logger.warning(f"❌ Error during WebSocket auth: {e}")
        return None

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Authenticated WebSocket for real-time AI chat with streaming responses."""
    user = await get_user_from_token(token, session)
    if not user:
        await websocket.send_json({"error": "Authentication failed"})
        await websocket.close(code=1008)  # Close with "Policy Violation"
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

            # Initialize LangGraph workflow.
            workflow = await rag_chat_workflow()
            initial_state = {
                "query": query,
                "retrieved_docs": [],
                "formatted_query": "",
                "response": "",
            }

            async for state in workflow.astream(initial_state, stream_mode="updates"):
                response_chunk = state.get("generate_response", {}).get("response", "")
                if response_chunk:
                    await manager.send_personal_message(response_chunk, user_id)

            # Notify all users of the new activity.
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
