from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.user_websocket_sessions = {}

from .websockets import *
from redis_om import Migrator

Migrator().run()

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)