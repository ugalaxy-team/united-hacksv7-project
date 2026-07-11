import socketio
from app.config import settings, GameMode
from app import app
from .schemas import User
from redis_om import get_redis_connection, NotFoundError
from .models import Player

sio = socketio.AsyncServer(cors_allowed_origins=settings.cors_origins, async_mode="asgi")
redis = get_redis_connection(url=settings.REDIS_OM_URL)

@sio.event
async def connect(sid, environ, auth):
    username = auth.get('username') if auth else None
    user_id = auth.get('userId') if auth else None

    if not username or not user_id:
        sio.disconnect(sid)
        raise ConnectionRefusedError("Unauthorized")

    app.state.user_websocket_sessions[sid] = User(
        username=username,
        id=user_id,
    )

@sio.event
async def disconnect(sid, reason):
    user: User = app.state.user_websocket_sessions[sid]
    try:
        player: Player = Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        return
    if player.current_queue:
        await leave_queue(sid)

    app.state.user_websocket_sessions.pop(sid, None)

@sio.on('queue:join')
async def queue_join(sid, data):
    user: User = app.state.user_websocket_sessions[sid]
    queue = f"queue:{data['queue']}"
    if user.id in redis.smembers(queue):
        return await sio.send({
            'message': 'You are already in queue!',
            'type': 'error'
        })
    game_mode = None
    for i in settings.game_modes:
        if i.name == data['queue']:
            game_mode = i
            break
    else:
        return await sio.send({
            'message': 'Wrong game mode!',
            'type': 'error'
        })
    if redis.scard(queue) + 1 >= game_mode.player_count:
        players = list(redis.smembers(queue))
        players.append(user.id)
        await start_game(players, game_mode)
        await sio.close_room(queue)
        return
    
    redis.sadd(queue, user.id)
    await sio.enter_room(sid, queue)
    try:
        player = Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        player = Player(
            user_id=user.id,
            username=user.username,
        )
        player.save()
    player.update(current_queue=queue)
    player_amount = redis.scard(queue)
    await sio.emit('queue:player_joined', {
        'id': user.id,
        'player_amount': player_amount
    }, to=queue, skip_sid=sid)
    return {
        'ok': True,
        'player_amount': player_amount
    }

@sio.on('queue:leave')
async def queue_leave(sid, data):
    user: User = app.state.user_websocket_sessions[sid]
    queue = f"queue:{data['queue']}"
    if not user.id in redis.smembers(queue):
        return await sio.send({
            'message': 'You are not in queue!',
            'type': 'error'
        })
    await leave_queue(sid)
    return {
        'ok': True,
    }

async def leave_queue(sid: str) -> None:
    user: User = app.state.user_websocket_sessions[sid]
    try:
        player: Player = Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        return
    queue = player.current_queue
    redis.srem(queue, user.id)
    await sio.leave_room(sid, queue)
    await sio.emit('queue:player_left', {
        'id': user.id,
        'player_amount': redis.scard(queue)
    }, to=queue, skip_sid=sid)
    if player:
        player.update(current_queue=None)

async def start_game(players: list[int], game_mode: GameMode) -> str:
    '''Returns created game's id'''
    # TODO: implement actual game start logic
    game = 'game'
    for sid, p in app.state.user_websocket_sessions.items():
        if p.id in players:
            await sio.enter_room(sid, game)
    await sio.emit('game:start', to=game)
    return game