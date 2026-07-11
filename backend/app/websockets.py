import socketio
from app.config import settings
from app import app
from .schemas import User

sio = socketio.AsyncServer(cors_allowed_origins=settings.cors_origins, async_mode="asgi")

@sio.event
async def connect(sid, environ, auth):
    username = auth.get('username') if auth else None
    user_id = auth.get('userId') if auth else None

    if not username or not user_id:
        raise ConnectionRefusedError("Unauthorized")

    app.state.user_websocket_sessions[sid] = User(
        username=username,
        id=user_id,
    )

@sio.event
async def disconnect(sid):
    app.state.user_websocket_sessions.pop(sid, None)