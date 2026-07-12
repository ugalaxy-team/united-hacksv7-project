import socketio
from aredis_om import get_redis_connection
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from app.config import settings

sio = socketio.AsyncServer(cors_allowed_origins=settings.cors_origins, async_mode="asgi", logger=settings.debug)
redis = get_redis_connection(url=settings.REDIS_OM_URL, decode_responses=True)
scheduler = AsyncIOScheduler()

scheduler.configure(misfire_grace_time=20)

scheduler.add_executor(AsyncIOExecutor(), 'default')