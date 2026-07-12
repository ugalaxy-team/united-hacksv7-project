from app.config import settings, GameMode
from app import app
from .schemas import User
from aredis_om import NotFoundError
from .models import Player, Game
import uuid
import datetime
import random
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from apscheduler.jobstores.base import JobLookupError
from datetime import timedelta
from .services import sio, redis, scheduler


def get_game_mode(name: str) -> GameMode | None:
    for gm in settings.game_modes:
        if gm.name == name:
            return gm
    return None


TRANSITION_JOB_PREFIX = 'transition'


def cancel_transition(game_id: str) -> None:
    try:
        scheduler.remove_job(f'{TRANSITION_JOB_PREFIX}:{game_id}')
    except JobLookupError:
        pass


def run_transition_now(game_id: str) -> None:
    try:
        scheduler.reschedule_job(
            f'{TRANSITION_JOB_PREFIX}:{game_id}',
            trigger='date',
            run_date=datetime.datetime.now(tz=datetime.timezone.utc)
        )
    except JobLookupError:
        pass


def schedule_transition(game_id: str, delay: int, func) -> None:
    scheduler.add_job(
        func,
        trigger='date',
        run_date=datetime.datetime.now(tz=datetime.timezone.utc) + timedelta(seconds=delay),
        id=f'{TRANSITION_JOB_PREFIX}:{game_id}',
        args=[game_id]
    )


async def go_to_voting(game_id: str) -> None:
    game = await get_game(game_id)
    if not game or game.phase != 'chatting':
        return
    room = f'game:{game_id}'
    game.phase = 'voting'
    game = await game.save()
    await sio.emit('game:voting', to=room)
    schedule_transition(game_id, game.voting_duration, go_to_results)


async def go_to_results(game_id: str) -> None:
    game = await get_game(game_id)
    if not game or game.phase != 'voting':
        return
    room = f'game:{game_id}'
    game.phase = 'results'
    game = await game.save()
    await sio.emit('game:results', [v.model_dump() for v in game.current_votes], to=room)
    schedule_transition(game_id, game.results_duration, go_to_next_round)


async def go_to_next_round(game_id: str) -> None:
    await new_round(game_id)


async def game_end(game_id: str) -> None:
    game = await get_game(game_id)
    if not game:
        return
    cancel_transition(game_id)
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
        await player.update(current_game=None)
        await player.save()
    await game.delete(game.pk)


async def new_round(game_id: str) -> None:
    game = await get_game(game_id)
    if not game:
        return
    if game.round == game.max_rounds:
        await game_end(game_id)
        return
    await game.update(current_votes=[], phase='chatting', round=game.round + 1)
    game = await game.save()
    await sio.emit('game:new_round', jsonable_encoder(game), to=f'game:{game_id}')
    schedule_transition(game_id, game.chatting_duration, go_to_voting)


async def leave_queue(sid: str) -> None:
    user: User = app.state.user_websocket_sessions[sid]
    player = await get_player(sid)
    if not player:
        return
    queue = player.current_queue
    if not queue:
        return
    await redis.srem(queue, user.id)
    await sio.leave_room(sid, queue)
    await sio.emit('queue:player_left', {
        'id': user.id,
        'player_amount': await redis.scard(queue)
    }, to=queue, skip_sid=sid)
    if player:
        await player.update(current_queue=None)


async def get_player(sid: str) -> Player | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        return await Player.find(Player.user_id == user.id).first()
    except (NotFoundError, ValidationError, ValueError):
        return None


async def get_or_create_player(sid: str) -> Player | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        return await Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        player = Player(
            user_id=user.id,
            username=user.username,
        )
        return await player.save()


async def get_current_queue(sid: str) -> str | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        player: Player = await Player.find(Player.user_id == user.id).first()
    except NotFoundError:
        return None
    return player.current_queue


async def get_game(game_id: str) -> Game | None:
    try:
        return await Game.find(Game.room_id == game_id).first()
    except (NotFoundError, ValidationError, ValueError):
        return None


async def get_current_game(sid: str) -> Game | None:
    user = app.state.user_websocket_sessions.get(sid)
    if not user:
        return None
    try:
        player: Player = await Player.find(Player.user_id == user.id).first()
    except (NotFoundError, ValidationError, ValueError):
        return None
    if not player.current_game:
        return None
    try:
        game: Game = await Game.find(Game.room_id == player.current_game).first()
    except (NotFoundError, ValidationError, ValueError):
        return None
    return game


async def start_game(players: list[Player], game_mode: GameMode) -> str:
    game = Game(
        room_id=uuid.uuid4().hex,
        round=1,
        messages_per_round=game_mode.messages_per_round,
        max_rounds=game_mode.rounds,
        phase='chatting',
        players=players,
        messages=[],
        current_votes=[],
        all_votes=[],
        game_mode=game_mode.name,
        chatting_duration=game_mode.chatting_duration,
        voting_duration=game_mode.voting_duration,
        results_duration=game_mode.results_duration,
    )
    game = await game.save()
    player_ids = [p.user_id for p in players]
    room = f'game:{game.room_id}'
    for sid, p in app.state.user_websocket_sessions.items():
        if p.id in player_ids:
            await leave_queue(sid)
            await sio.enter_room(sid, room)
            player = await get_player(sid)
            if player:
                player.current_game = game.room_id
                await player.save()
    await sio.emit('game:start', jsonable_encoder(game), to=room)
    schedule_transition(game.room_id, game.chatting_duration, go_to_voting)
    return room
