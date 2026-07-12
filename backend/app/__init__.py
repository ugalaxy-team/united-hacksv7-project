from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import socketio

from .config import settings
from aredis_om import Migrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .services import scheduler
    await Migrator().run()
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

from .routes import router

app.include_router(router)

from .websockets import *
from .services import sio

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
