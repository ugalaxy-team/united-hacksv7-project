from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import socketio

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .services import scheduler
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.user_websocket_sessions = {}

from .websockets import *
from .services import sio
from redis_om import Migrator

Migrator().run()

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)