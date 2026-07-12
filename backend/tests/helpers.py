from aredis_om import NotFoundError
from app import app
from app.schemas import User
from app.models import Player, Game
from app.config import settings


async def create_user(sid: str, username: str = "alice", user_id: str | None = None):
    uid = user_id or f"user_{sid}"
    app.state.user_websocket_sessions[sid] = User(username=username, id=uid)
    return uid


async def create_player(user_id: str, username: str = "alice"):
    p = Player(user_id=user_id, username=username)
    await p.save()
    return p


async def create_players(sids: list[str]) -> list[Player]:
    players = []
    for s in sids:
        u = app.state.user_websocket_sessions[s]
        p = await create_player(u.id, u.username)
        players.append(p)
    return players


def get_standard_mode():
    return next(gm for gm in settings.game_modes if gm.name == "standard")


async def find_player(user_id: str) -> Player | None:
    try:
        return await Player.find(Player.user_id == user_id).first()
    except NotFoundError:
        return None


async def find_game(room_id: str) -> Game | None:
    try:
        return await Game.find(Game.room_id == room_id).first()
    except NotFoundError:
        return None
