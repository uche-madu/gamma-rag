from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..database import get_async_session
from ..services.article import embed_articles

scheduler = AsyncIOScheduler()

async def scheduled_embedding():
    """Scheduled job to embed new articles every 6 hours"""
    async for session in get_async_session():
        await embed_articles(session)

def start_scheduler():
    """Starts the scheduler when FastAPI starts"""
    scheduler.add_job(
        scheduled_embedding, 
        "interval", hours=6, 
        next_run_time=datetime.now()
    )
    scheduler.start()

def shutdown_scheduler():
    """Stops the scheduler when FastAPI shuts down"""
    scheduler.shutdown()
