from app.config import settings
from app import app
from .schemas import User
from aredis_om import NotFoundError
from .models import Player, Message, Vote
import datetime
from fastapi.encoders import jsonable_encoder
from .services import sio, redis
from .util import (
    leave_queue, get_player, get_or_create_player, get_current_game,
    start_game, run_transition_now,
)


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
    player = await get_player(sid)
    await leave_queue(sid)
    if player:
        await player.update(current_game=None)
        await player.save()

    app.state.user_websocket_sessions.pop(sid, None)


@sio.on('queue:join')
async def queue_join(sid, data):
    user: User = app.state.user_websocket_sessions[sid]
    queue = f"queue:{data['queue']}"
    if user.id in await redis.smembers(queue):
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
    await redis.sadd(queue, user.id)
    await sio.enter_room(sid, queue)
    player = await get_or_create_player(sid)
    await player.update(current_queue=queue)
    player = await player.save()

    player_amount = await redis.scard(queue)
    if player_amount >= game_mode.player_count:
        player_ids = await redis.smembers(queue)
        players: list[Player] = []
        for pid in player_ids:
            p = await Player.find(Player.user_id == pid).first()
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
    if user.id not in await redis.smembers(queue):
        await sio.emit('message', {
            'message': 'You are not in queue!',
            'type': 'error'
        }, to=sid)
        return
    await leave_queue(sid)
    return {
        'ok': True,
    }


@sio.on('game:vote')
async def game_vote(sid, data):
    game = await get_current_game(sid)
    if not game:
        return
    if game.phase != 'voting':
        await sio.emit('message', {
            'message': 'Action is prohibited!',
            'type': 'error'
        }, to=sid)
        return
    room = f'game:{game.room_id}'
    voter = await get_player(sid)
    if not voter:
        return
    if data['user_id'] == voter.user_id:
        await sio.emit('message', {
            'message': "Can't vote for yourself!",
            'type': 'error'
        }, to=sid)
        return
    try:
        vote_for = await Player.find(Player.user_id==data['user_id']).first()
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
    await vote.save()
    game.current_votes.append(vote)
    game.all_votes.append(vote)
    game = await game.save()
    await sio.emit('game:vote_casted', jsonable_encoder(vote), to=room)
    all_voted = all(
        any(v.vote_by.user_id == p.user_id for v in game.current_votes)
        for p in game.players
    )
    if all_voted:
        run_transition_now(game.room_id)


@sio.on('game:message')
async def game_message(sid, data):
    try:
        game = await get_current_game(sid)
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
    player = await get_player(sid)
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
    message = await message.save()
    game.messages.append(message)
    game = await game.save()
    await sio.emit('game:message_sent', jsonable_encoder(message), to=room)

    all_sent = all(
        sum(1 for m in game.messages if m.sender.user_id == p.user_id and m.round == game.round) >= game.messages_per_round
        for p in game.players
    )

    if all_sent:
        run_transition_now(game.room_id)
