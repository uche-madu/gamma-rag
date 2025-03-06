from contextlib import asynccontextmanager
from typing_extensions import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import User
from .services.user_manager import current_active_user
from .routers.auth import router as auth_router
from .routers.article import router as article_router
from .routers.chat import router as chat_router
from .scheduler.embedding_scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()

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
routers = [auth_router, article_router, chat_router]  # List of all routers
for router in routers:
    app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Gamma Financial Advisor API! 🚀",
        "docs": "Visit /docs for the interactive API documentation (Swagger UI).",
        "redoc": "Visit /redoc for the alternative API documentation (ReDoc).",
        "info": "Use this API to interact with financial insights, AI-powered analysis, and more."
    }


# Protected Route (Only logged-in users)
@app.get("/authenticated-route")
async def authenticated_route(user: Annotated[User, Depends(current_active_user)]):
    return {"message": f"Hello {user.username}!"}

