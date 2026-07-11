import socketio
from app.config import settings, GameMode
from app import app
from .schemas import User
from redis_om import get_redis_connection, NotFoundError
from .models import Player, Game, Message, Vote
import uuid
import datetime
import asyncio
import random
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

sio = socketio.AsyncServer(cors_allowed_origins=settings.cors_origins, async_mode="asgi", logger=settings.debug)
redis = get_redis_connection(url=settings.REDIS_OM_URL, decode_responses=True)

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
    player = get_player(sid)
    await leave_queue(sid)
    if player:
        player.update(current_game=None)
        player.save()

    app.state.user_websocket_sessions.pop(sid, None)

@sio.on('queue:join')
async def queue_join(sid, data):
    user: User = app.state.user_websocket_sessions[sid]
    queue = f"queue:{data['queue']}"
    if user.id in redis.smembers(queue):
        await sio.emit('message', {
            'message': 'You are already in queue!',
            'type': 'error'
        }, to=sid)
        return
    game_mode = None
    for i in settings.game_modes:
        if i.name == data['queue']:
            game_mode = i
            break
    else:
        await sio.emit('message', {
            'message': 'Wrong game mode!',
            'type': 'error'
        }, to=sid)
        return
    redis.sadd(queue, user.id)
    await sio.enter_room(sid, queue)
    player = get_or_create_player(sid)
    player.update(current_queue=queue)
    player = player.save()

    player_amount = redis.scard(queue)
    if player_amount >= game_mode.player_count:
        player_ids = redis.smembers(queue)
        players: list[Player] = []
        for pid in player_ids:
            p = Player.find(Player.user_id == pid).first()
            if p:
                players.append(p)
        await start_game(players, game_mode)
        await sio.close_room(queue)
        return

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
        await sio.emit('message', {
            'message': 'You are not in queue!',
            'type': 'error'
        }, to=sid)
        return
    await leave_queue(sid)
    return {
        'ok': True,
    }

async def leave_queue(sid: str) -> None:
    user: User = app.state.user_websocket_sessions[sid]
    player = get_player(sid)
    if not player:
        return
    queue = player.current_queue
    if not queue:
        return
    redis.srem(queue, user.id)
    await sio.leave_room(sid, queue)
    await sio.emit('queue:player_left', {
        'id': user.id,
        'player_amount': redis.scard(queue)
    }, to=queue, skip_sid=sid)
    if player:
        player.update(current_queue=None)

async def game_end(game_id: str) -> None:
    game = get_game(game_id)
    if not game:
        return
    room = f'game:{game_id}'
    data = jsonable_encoder(game.model_dump())
    ai_player = random.choice(game.players)
    victory = False
    votes = {}
    for i in game.all_votes:
        votes[i.vote_for.user_id] = votes.get(i.vote_for.user_id, 0) + 1

    for k, v in votes.items():
        if v == max(votes.values()) and k == ai_player.user_id:
            victory = True
            break

    data['ai_player'] = jsonable_encoder(ai_player)
    data['victory'] = victory
    await sio.emit('game:end', data, to=room)
    await sio.close_room(room)

    for player in game.players:
        player.update(current_game=None)
        player.save()
    game.delete()

async def new_round(game_id: str) -> None:
    game = get_game(game_id)
    if not game:
        return
    room = f'game:{game_id}'
    if game.round == game.max_rounds:
        await game_end(game_id)
        return
    game.update(current_votes=[], phase='chatting', round=game.round + 1)
    game = game.save()
    await sio.emit('game:new_round', jsonable_encoder(game), to=room)

async def send_results(game_id: str) -> None:
    game = get_game(game_id)
    if not game:
        return
    room = f'game:{game_id}'
    await sio.emit('game:results', [v.model_dump() for v in game.current_votes], to=room)
    await asyncio.sleep(5)
    await new_round(game_id)

@sio.on('game:vote')
async def game_vote(sid, data):
    game = get_current_game(sid)
    if not game:
        return
    if game.phase != 'voting':
        await sio.emit('message', {
            'message': 'Action is prohibited!',
            'type': 'error'
        }, to=sid)
        return
    room = f'game:{game.room_id}'
    voter = get_player(sid)
    if not voter:
        return
    if data['user_id'] == voter.user_id:
        await sio.emit('message', {
            'message': "Can't vote for yourself!",
            'type': 'error'
        }, to=sid)
        return
    try:
        vote_for = Player.find(Player.user_id==data['user_id']).first()
    except NotFoundError:
        await sio.emit('message', {
            'message': 'Player to vote for not found!',
            'type': 'error'
        }, to=sid)
        return
    already_voted = any(v.vote_by.user_id == voter.user_id for v in game.current_votes)
    if already_voted:
        await sio.emit('message', {
            'message': 'You have already voted!',
            'type': 'error'
        }, to=sid)
        return

    vote = Vote(
        vote_for=vote_for,
        vote_by=voter
    )
    vote.save()
    game.current_votes.append(vote)
    game.all_votes.append(vote)
    game = game.save()
    await sio.emit('game:vote_casted', jsonable_encoder(vote), to=room)
    all_voted = all(
        any(v.vote_by.user_id == p.user_id for v in game.current_votes)
        for p in game.players
    )
    if all_voted:
        game.phase = 'results'
        game = game.save()
        await send_results(game.room_id)


@sio.on('game:message')
async def game_message(sid, data):
    try:
        game = get_current_game(sid)
    except Exception:
        await sio.emit('message', {
            'message': 'Unable to load game state.',
            'type': 'error'
        }, to=sid)
        return

    if not game:
        await sio.emit('message', {
            'message': 'You are not in an active game.',
            'type': 'error'
        }, to=sid)
        return
    if game.phase != 'chatting':
        await sio.emit('message', {
            'message': 'Action is prohibited!',
            'type': 'error'
        }, to=sid)
        return
    room = f'game:{game.room_id}'
    player = get_player(sid)
    if not player:
        return
    message_count = sum(1 for m in game.messages if m.sender.user_id == player.user_id and m.round == game.round)
    if message_count >= game.messages_per_round:
        await sio.emit('message', {
            'message': 'You already sent maximum number of messages allowed!',
            'type': 'error'
        }, to=sid)
        return
    message = Message(
        text=data['message'],
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        room_id=game.room_id,
        sender=player,
        round=game.round
    )
    message = message.save()
    game.messages.append(message)
    game = game.save()
    await sio.emit('game:message_sent', jsonable_encoder(message), to=room)

    all_sent = all(
        sum(1 for m in game.messages if m.sender.user_id == p.user_id and m.round == game.round) >= game.messages_per_round
        for p in game.players
    )

    if all_sent:
        game.phase = 'voting'
        game = game.save()
        await sio.emit('game:voting', to=room)


def get_player(sid: str) -> Player | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        return Player.find(Player.user_id == user.id).first()
    except (NotFoundError, ValidationError, ValueError):
        return None


def get_or_create_player(sid: str) -> Player | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        return Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        player = Player(
            user_id=user.id,
            username=user.username,
        )
        return player.save()


def get_current_queue(sid: str) -> str | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        player: Player = Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        return None
    return player.current_queue

def get_game(game_id: str) -> Game | None:
    try:
        return Game.find(Game.room_id == game_id).first()
    except (NotFoundError, ValidationError, ValueError):
        return None

def get_current_game(sid: str) -> Game | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        player: Player = Player.find(Player.user_id == user.id).first()
    except (NotFoundError, ValidationError, ValueError):
        return None
    if not player.current_game:
        return None
    try:
        game: Game = Game.find(Game.room_id == player.current_game).first()
    except (NotFoundError, ValidationError, ValueError):
        return None
    return game


async def start_game(players: list[Player], game_mode: GameMode) -> str:
    '''Returns created game's id'''

    game = Game(
        room_id=uuid.uuid4().hex,
        round=1,
        messages_per_round=game_mode.messages_per_round,
        max_rounds=game_mode.rounds,
        phase='chatting',
        players=players,
        messages=[],
        current_votes=[],
        all_votes=[]
    )
    game = game.save()
    player_ids = [p.user_id for p in players]
    room = f'game:{game.room_id}'
    for sid, p in app.state.user_websocket_sessions.items():
        if p.id in player_ids:
            await leave_queue(sid)
            await sio.enter_room(sid, room)
            player = get_player(sid)
            if player:
                player.current_game = game.room_id
                player.save()
    await sio.emit('game:start', jsonable_encoder(game), to=room)
    return room
