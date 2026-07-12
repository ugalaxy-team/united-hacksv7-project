import asyncio
import pytest
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app import app
from app.models import Game
from app.websockets import connect, disconnect, queue_join, queue_leave, game_vote, game_message
from tests.helpers import create_user, create_player, create_players, find_player, find_game
from app.util import go_to_voting, schedule_transition, get_current_game

class TestConnect:
    async def test_success(self, sid):
        await connect(sid, {}, {"username": "alice", "userId": "uid1"})
        session = app.state.user_websocket_sessions[sid]
        assert session.username == "alice"
        assert session.id == "uid1"

    async def test_missing_username(self, sid):
        with pytest.raises(ConnectionRefusedError):
            await connect(sid, {}, {"userId": "uid1"})
        assert sid not in app.state.user_websocket_sessions

    async def test_missing_userId(self, sid):
        with pytest.raises(ConnectionRefusedError):
            await connect(sid, {}, {"username": "alice"})
        assert sid not in app.state.user_websocket_sessions

    async def test_missing_both(self, sid):
        with pytest.raises(ConnectionRefusedError):
            await connect(sid, {}, {})
        assert sid not in app.state.user_websocket_sessions

    async def test_missing_auth(self, sid):
        with pytest.raises(ConnectionRefusedError):
            await connect(sid, {}, None)
        assert sid not in app.state.user_websocket_sessions

class TestDisconnect:
    async def test_with_player(self, sid, mock_sio):
        await create_user(sid)
        await create_player(f"user_{sid}")

        await disconnect(sid, "client disconnect")

        assert sid not in app.state.user_websocket_sessions
        player = await find_player(f"user_{sid}")
        assert player is not None
        assert player.current_game is None

    async def test_without_player(self, sid, mock_sio):
        await create_user(sid)
        await disconnect(sid, "client disconnect")
        assert sid not in app.state.user_websocket_sessions

class TestQueueJoin:
    async def test_success(self, sid, mock_sio):
        await create_user(sid)
        result = await queue_join(sid, {"queue": "standard"})

        assert result["ok"] is True
        assert result["player_amount"] == 1

        mock_sio.enter_room.assert_awaited_once_with(sid, "queue:standard")

        player = await find_player(f"user_{sid}")
        assert player is not None
        assert player.current_queue == "queue:standard"

    async def test_already_in_queue(self, sid, mock_sio):
        await create_user(sid)
        await queue_join(sid, {"queue": "standard"})
        mock_sio.emit.reset_mock()

        result = await queue_join(sid, {"queue": "standard"})

        assert result is None
        mock_sio.emit.assert_awaited_once_with("message", {
            "message": "You are already in queue!",
            "type": "error"
        }, to=sid)

    async def test_wrong_game_mode(self, sid, mock_sio):
        await create_user(sid)
        result = await queue_join(sid, {"queue": "nonexistent"})

        assert result is None
        mock_sio.emit.assert_awaited_once_with("message", {
            "message": "Wrong game mode!",
            "type": "error"
        }, to=sid)

    async def test_auto_start_game_when_enough_players(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "user_a")
        await create_user(sid2, "bob", "user_b")

        await queue_join(sid, {"queue": "standard"})
        mock_sio.emit.reset_mock()
        mock_sio.enter_room.reset_mock()

        await queue_join(sid2, {"queue": "standard"})

        game_start_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:start"]
        assert len(game_start_calls) >= 1

        mock_sio.close_room.assert_awaited_once_with("queue:standard")

        games = await Game.find().all()
        assert len(games) >= 1
        assert len(games[0].players) == 2

    async def test_player_amount_below_threshold(self, sid, sid2, mock_sio):
        await create_user(sid)
        await create_user(sid2)

        result = await queue_join(sid, {"queue": "standard"})
        assert result == {"ok": True, "player_amount": 1}
        result = await queue_join(sid2, {"queue": "standard"})

        assert result is None

    async def test_creates_player_if_not_exists(self, sid, mock_sio):
        await create_user(sid, "charlie", "user_c")

        await queue_join(sid, {"queue": "standard"})

        player = await find_player("user_c")
        assert player is not None
        assert player.username == "charlie"

class TestQueueLeave:
    async def test_success(self, sid, mock_sio):
        await create_user(sid)
        await queue_join(sid, {"queue": "standard"})
        mock_sio.emit.reset_mock()

        result = await queue_leave(sid, {"queue": "standard"})
        assert result["ok"] is True

        mock_sio.emit.assert_any_await("queue:player_left", {
            "id": f"user_{sid}",
            "player_amount": 0
        }, to="queue:standard", skip_sid=sid)
        mock_sio.leave_room.assert_awaited()

    async def test_not_in_queue(self, sid, mock_sio):
        await create_user(sid)

        result = await queue_leave(sid, {"queue": "standard"})

        assert result is None
        mock_sio.emit.assert_awaited_once_with("message", {
            "message": "You are not in queue!",
            "type": "error"
        }, to=sid)


class TestGameVote:
    @pytest.fixture(autouse=True)
    async def setup_game(self, sid, sid2):
        await create_user(sid, "alice", "user_a")
        await create_user(sid2, "bob", "user_b")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="game_001",
            round=1, max_rounds=3, messages_per_round=5,
            phase="voting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        for p in players:
            p.current_game = "game_001"
            await p.save()

    async def test_success(self, sid, mock_sio):
        await game_vote(sid, {"user_id": "user_b"})
        vote_casted_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:vote_casted"]
        assert len(vote_casted_calls) >= 1

    async def test_not_in_game(self, sid, mock_sio):
        app.state.user_websocket_sessions.clear()
        await create_user(sid, "stranger", "unknown_user")
        await game_vote(sid, {"user_id": "user_b"})
        vote_casted_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:vote_casted"]
        assert len(vote_casted_calls) == 0

    async def test_wrong_phase(self, sid, mock_sio):
        game = await find_game("game_001")
        game.phase = "chatting"
        await game.save()
        await game_vote(sid, {"user_id": "user_b"})
        mock_sio.emit.assert_any_await("message", {
            "message": "Action is prohibited!", "type": "error"
        }, to=sid)

    async def test_voting_for_self(self, sid, mock_sio):
        await game_vote(sid, {"user_id": "user_a"})
        mock_sio.emit.assert_any_await("message", {
            "message": "Can't vote for yourself!", "type": "error"
        }, to=sid)

    async def test_player_to_vote_not_found(self, sid, mock_sio):
        await game_vote(sid, {"user_id": "nonexistent"})
        mock_sio.emit.assert_any_await("message", {
            "message": "Player to vote for not found!", "type": "error"
        }, to=sid)

    async def test_already_voted(self, sid, mock_sio):
        await game_vote(sid, {"user_id": "user_b"})
        mock_sio.emit.reset_mock()
        await game_vote(sid, {"user_id": "user_b"})
        mock_sio.emit.assert_any_await("message", {
            "message": "You have already voted!", "type": "error"
        }, to=sid)

class TestGameMessage:
    @pytest.fixture(autouse=True)
    async def setup_game(self, sid, sid2):
        await create_user(sid, "alice", "user_a")
        await create_user(sid2, "bob", "user_b")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="game_002",
            round=1, max_rounds=3, messages_per_round=1,
            phase="chatting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        for p in players:
            p.current_game = "game_002"
            await p.save()

    async def test_success(self, sid, mock_sio):
        await game_message(sid, {"message": "Hello!"})
        msg_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:message_sent"]
        assert len(msg_calls) >= 1

    async def test_not_in_game(self, sid, mock_sio):
        app.state.user_websocket_sessions.clear()
        await create_user(sid, "stranger", "unknown_user")
        await game_message(sid, {"message": "Hello!"})
        mock_sio.emit.assert_any_await("message", {
            "message": "You are not in an active game.", "type": "error"
        }, to=sid)

    async def test_wrong_phase(self, sid, mock_sio):
        game = await find_game("game_002")
        game.phase = "voting"
        await game.save()
        await game_message(sid, {"message": "Hello!"})
        mock_sio.emit.assert_any_await("message", {
            "message": "Action is prohibited!", "type": "error"
        }, to=sid)

    async def test_max_messages_reached(self, sid, mock_sio):
        await game_message(sid, {"message": "First"})
        mock_sio.emit.reset_mock()
        await game_message(sid, {"message": "Second"})
        mock_sio.emit.assert_any_await("message", {
            "message": "You already sent maximum number of messages allowed!", "type": "error"
        }, to=sid)

    async def test_all_sent_triggers_transition(self, sid, sid2, mock_sio):
        from app.services import scheduler

        scheduler.start()
        try:
            transition_done = asyncio.Event()

            def on_job_event(event):
                if event.job_id == "transition:game_002":
                    transition_done.set()

            scheduler.add_listener(on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

            game = await get_current_game(sid)
            schedule_transition(game.room_id, game.chatting_duration, go_to_voting)
            game = await find_game("game_002")
            await game_message(sid, {"message": "From A"})
            await game_message(sid2, {"message": "From B"})
            await asyncio.wait_for(transition_done.wait(), timeout=5)
            game = await find_game("game_002")
            assert game.phase == "voting"
        finally:
            scheduler.shutdown(wait=False)

    async def test_game_deleted(self, sid, mock_sio):
        game = await find_game("game_002")
        await game.delete(game.pk)
        await game_message(sid, {"message": "Hello!"})
        mock_sio.emit.assert_any_await("message", {
            "message": "You are not in an active game.", "type": "error"
        }, to=sid)
