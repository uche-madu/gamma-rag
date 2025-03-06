import urllib.parse
from typing import Dict, Optional
from uuid import UUID

from fastapi import WebSocket
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from ..services.user_manager import JWT_SECRET, get_user_db
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


async def get_user_from_token(token: str, session: AsyncSession) -> Optional[User]:
    """Authenticate user by decoding the JWT token and fetching user from the DB."""
    try:
        # Unquote token in case it was URL encoded.
        token = urllib.parse.unquote(token)
        logger.info(f"🔐 Authenticating WebSocket user with token: {token}")

        # Decode the token using the expected audience (adjust if necessary).
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="fastapi-users:auth")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload: no subject found")
        user_id = UUID(user_id)

        # Get the user_db instance.
        user_db_gen = get_user_db(session)
        user_db = await user_db_gen.__anext__()  # Get the first yielded value

        # Fetch the user.
        user = await user_db.get(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")
        return user

    except JWTError as e:
        logger.warning(f"❌ JWT decode error: {e}")
        return None
    except Exception as e:
        logger.warning(f"❌ Error during WebSocket auth: {e}")
        return None
