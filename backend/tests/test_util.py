from unittest.mock import ANY
from app import app
from app.models import Game
from app.services import redis
from app.util import (
    get_player, get_or_create_player, get_current_queue, get_game, get_current_game,
    leave_queue, start_game, game_end, new_round, go_to_voting, go_to_results,
)
from tests.helpers import create_user, create_player, create_players, find_player, find_game, get_standard_mode


class TestUtilGetPlayer:
    async def test_found(self, sid):
        await create_user(sid)
        await create_player(f"user_{sid}")
        player = await get_player(sid)
        assert player is not None
        assert player.user_id == f"user_{sid}"

    async def test_not_found(self, sid):
        await create_user(sid)
        player = await get_player(sid)
        assert player is None

    async def test_user_not_in_session(self):
        player = await get_player("nonexistent")
        assert player is None


class TestUtilGetOrCreatePlayer:
    async def test_existing(self, sid):
        await create_user(sid)
        await create_player(f"user_{sid}")
        player = await get_or_create_player(sid)
        assert player is not None
        assert player.user_id == f"user_{sid}"

    async def test_creates_new(self, sid):
        await create_user(sid, "new_user", "new_uid")
        player = await get_or_create_player(sid)
        assert player is not None
        assert player.user_id == "new_uid"
        assert player.username == "new_user"

    async def test_no_session(self):
        player = await get_or_create_player("nonexistent")
        assert player is None


class TestUtilGetCurrentQueue:
    async def test_found(self, sid):
        await create_user(sid)
        p = await create_player(f"user_{sid}")
        p.current_queue = "queue:standard"
        await p.save()
        queue = await get_current_queue(sid)
        assert queue == "queue:standard"

    async def test_not_found(self, sid):
        await create_user(sid)
        queue = await get_current_queue(sid)
        assert queue is None

    async def test_no_session(self):
        queue = await get_current_queue("nonexistent")
        assert queue is None


class TestUtilGetGame:
    async def test_found(self):
        game = Game(
            room_id="g_found", round=1, max_rounds=3, messages_per_round=5,
            phase="chatting", players=[], messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        found = await get_game("g_found")
        assert found is not None
        assert found.room_id == "g_found"

    async def test_not_found(self):
        found = await get_game("nonexistent")
        assert found is None


class TestUtilGetCurrentGame:
    async def test_found(self, sid):
        await create_user(sid)
        p = await create_player(f"user_{sid}")
        game = Game(
            room_id="g_curr", round=1, max_rounds=3, messages_per_round=5,
            phase="chatting", players=[], messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        p.current_game = "g_curr"
        await p.save()
        found = await get_current_game(sid)
        assert found is not None
        assert found.room_id == "g_curr"

    async def test_no_player(self, sid):
        await create_user(sid)
        found = await get_current_game(sid)
        assert found is None

    async def test_no_current_game(self, sid):
        await create_user(sid)
        p = await create_player(f"user_{sid}")
        p.current_game = None
        await p.save()
        found = await get_current_game(sid)
        assert found is None

    async def test_no_session(self):
        found = await get_current_game("nonexistent")
        assert found is None


class TestUtilLeaveQueue:
    async def _setup(self, sid):
        await create_user(sid)
        p = await create_player(f"user_{sid}")
        p.current_queue = "queue:test"
        await p.save()
        await redis.sadd("queue:test", f"user_{sid}")
        return f"user_{sid}"

    async def test_success(self, sid, mock_sio):
        uid = await self._setup(sid)
        await leave_queue(sid)
        members = await redis.smembers("queue:test")
        assert uid not in members
        player = await find_player(uid)
        assert player.current_queue is None
        mock_sio.emit.assert_any_await("queue:player_left", {
            "id": uid, "game_mode": "test", "player_amount": 0
        }, to="queue:test")

    async def test_no_player(self, sid, mock_sio):
        await create_user(sid)
        await leave_queue(sid)
        assert sid in app.state.user_websocket_sessions

    async def test_no_queue(self, sid, mock_sio):
        await create_user(sid)
        p = await create_player(f"user_{sid}")
        assert p.current_queue is None
        await leave_queue(sid)


class TestUtilStartGame:
    async def test_creates_game(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        room = await start_game(players, get_standard_mode())
        assert room.startswith("game:")
        game_room_id = room.split(":", 1)[1]
        game = await get_game(game_room_id)
        assert game is not None
        assert len(game.players) == 3
        assert game.phase == "chatting"
        game_start_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:start"]
        assert len(game_start_calls) >= 1

    async def test_updates_players(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        await start_game(players, get_standard_mode())
        player = await find_player("ua")
        assert player.current_game is not None
        player2 = await find_player("ub")
        assert player2.current_game is not None


class TestUtilGameEnd:
    async def test_game_end(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="endtest", round=2, max_rounds=2, messages_per_round=5,
            phase="chatting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        for p in players:
            p.current_game = "endtest"
            await p.save()
        await game_end("endtest")
        found = await find_game("endtest")
        assert found is None
        for p in players:
            refreshed = await find_player(p.user_id)
            assert refreshed.current_game is None
        mock_sio.emit.assert_any_await("game:end", ANY, to="game:endtest")
        mock_sio.close_room.assert_awaited_once_with("game:endtest")

    async def test_game_not_found(self, mock_sio):
        await game_end("nonexistent")
        mock_sio.emit.assert_not_awaited()


class TestUtilNewRound:
    async def test_advances_round(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="nr_test", round=1, max_rounds=3, messages_per_round=5,
            phase="voting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        await new_round("nr_test")
        game = await find_game("nr_test")
        assert game.round == 2
        assert game.phase == "chatting"

    async def test_last_round_triggers_end(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="nr_last", round=3, max_rounds=3, messages_per_round=5,
            phase="voting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        await new_round("nr_last")
        found = await find_game("nr_last")
        assert found is None
        mock_sio.emit.assert_any_await("game:end", ANY, to="game:nr_last")

    async def test_game_not_found(self, mock_sio):
        await new_round("nonexistent")
        mock_sio.emit.assert_not_awaited()


class TestUtilGoToVoting:
    async def test_transitions_to_voting(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="gtv_test", round=1, max_rounds=3, messages_per_round=5,
            phase="chatting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        await go_to_voting("gtv_test")
        game = await find_game("gtv_test")
        assert game.phase == "voting"
        mock_sio.emit.assert_any_await("game:voting", to="game:gtv_test")

    async def test_wrong_phase(self, mock_sio):
        await go_to_voting("nonexistent")
        mock_sio.emit.assert_not_awaited()


class TestUtilGoToResults:
    async def test_transitions_to_results(self, sid, sid2, mock_sio):
        await create_user(sid, "alice", "ua")
        await create_user(sid2, "bob", "ub")
        players = await create_players([sid, sid2])
        game = Game(
            room_id="gtr_test", round=1, max_rounds=3, messages_per_round=5,
            phase="voting", players=players, messages=[], current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        await go_to_results("gtr_test")
        game = await find_game("gtr_test")
        assert game.phase == "results"
        mock_sio.emit.assert_any_await("game:results", [], to="game:gtr_test")

    async def test_wrong_phase(self, mock_sio):
        await go_to_results("nonexistent")
        mock_sio.emit.assert_not_awaited()
