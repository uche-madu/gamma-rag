from contextlib import asynccontextmanager
from typing_extensions import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import User
from .services.user_manager import current_active_user
from .routers.auth import router as auth_router
from .routers.article import router as article_router
from .routers.chat import router as chat_router
from .routers.websocket_chat import router as websocket_chat_router
from .scheduler.embedding_scheduler import start_scheduler, shutdown_scheduler
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app lifecycle events."""
    logger.info("🚀 Starting application...")
    
    # Start scheduler for background tasks
    start_scheduler()

    yield  # The app runs during this time

    # Cleanup on shutdown
    shutdown_scheduler()
    logger.info("🛑 Shutting down application...")

app = FastAPI(lifespan=lifespan, title="Gamma Financial Advisor API", version="1.0")


# CORS Middleware (Allow frontend to communicate with backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
routers = [auth_router, article_router, chat_router, websocket_chat_router]  # List of all routers
for router in routers:
    app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Gamma Financial Advisor API! 🚀",
        "docs": "Visit /docs for the interactive API documentation (Swagger UI).",
        "redoc": "Visit /redoc for the alternative API documentation (ReDoc).",
        "info": "Use this API to interact with financial insights, AI-powered analysis, and more.",
        "authentication": {
            "register": "Send a POST request to /auth/register with your details.",
            "login": "Authenticate at /auth/jwt/login to get a JWT token.",
            "protected_routes": "Include the token in the Authorization header as 'Bearer <token>' for protected routes."
        },
        "usage": {
            "financial_advice": "Send a POST request to /chat with {'query': 'your financial question'} to receive insights.",
            "embed_articles": "Trigger embeddings for articles by sending a POST request to /articles/embed-all.",
        },
        "websocket": {
            "real_time_chat": "Connect to /chat/ws with a valid token for real-time AI-powered financial conversations."
        }
    }



# Protected Route (Only logged-in users)
@app.get("/authenticated-route")
async def authenticated_route(user: Annotated[User, Depends(current_active_user)]):
    return {"message": f"Hello {user.username}!"}

