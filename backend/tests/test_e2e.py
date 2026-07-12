from unittest.mock import ANY
from app import app
from app.models import Game, Vote
from app.websockets import connect, queue_join, game_vote, game_message
from app.util import go_to_voting, go_to_results, new_round, game_end
from tests.helpers import create_players, find_game


class TestE2EFullGame:
    async def test_full_game_one_round(self, sid, sid2, mock_sio):
        """2 players, 1 round: connect -> queue -> start -> message -> vote -> results -> end."""
        await connect(sid, {}, {"username": "alice", "userId": "ua"})
        await connect(sid2, {}, {"username": "bob", "userId": "ub"})
        assert len(app.state.user_websocket_sessions) == 2

        mock_sio.emit.reset_mock()
        await queue_join(sid, {"queue": "quickplay"})

        mock_sio.emit.reset_mock()
        await queue_join(sid2, {"queue": "quickplay"})

        game_start_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:start"]
        assert len(game_start_calls) >= 1

        games = await Game.find().all()
        assert len(games) >= 1
        game = games[-1]
        assert len(game.players) == 3
        assert game.game_mode == "quickplay"
        assert game.phase == "chatting"
        game_id = game.room_id

        mock_sio.emit.reset_mock()
        await game_message(sid, {"message": "Hello from Alice"})
        msg_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:message_sent"]
        assert len(msg_calls) >= 1

        mock_sio.emit.reset_mock()
        await game_message(sid2, {"message": "Hello from Bob"})
        msg_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:message_sent"]
        assert len(msg_calls) >= 1

        await go_to_voting(game_id)
        game = await find_game(game_id)
        assert game.phase == "voting"

        mock_sio.emit.reset_mock()
        await game_vote(sid, {"user_id": "ub"})
        vote_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:vote_casted"]
        assert len(vote_calls) >= 1

        mock_sio.emit.reset_mock()
        await game_vote(sid2, {"user_id": "ua"})
        vote_calls = [c for c in mock_sio.emit.call_args_list if c[0][0] == "game:vote_casted"]
        assert len(vote_calls) >= 1

        await go_to_results(game_id)
        game = await find_game(game_id)
        assert game.phase == "results"
        mock_sio.emit.assert_any_await("game:results", ANY, to=f"game:{game_id}")

        game.round = game.max_rounds
        await game.save()

        await new_round(game_id)
        found = await find_game(game_id)
        assert found is None
        mock_sio.emit.assert_any_await("game:end", ANY, to=f"game:{game_id}")

    async def test_full_game_with_victory(self, sid, sid2, mock_sio):
        """2 players, single round, AI player determined as impostor -- verify victory logic."""
        await connect(sid, {}, {"username": "alice", "userId": "ua"})
        await connect(sid2, {}, {"username": "bob", "userId": "ub"})

        players = await create_players([sid, sid2])

        game = Game(
            room_id="victory_test", round=1, max_rounds=1, messages_per_round=5,
            phase="chatting", topic="test topic", players=players, messages=[],
            current_votes=[], all_votes=[],
            game_mode="standard", chatting_duration=20, voting_duration=10, results_duration=5,
        )
        await game.save()
        for p in players:
            p.current_game = game.room_id
            await p.save()

        ai_player = players[0]
        voter = players[1]

        vote = Vote(vote_for=ai_player, vote_by=voter)
        await vote.save()
        game.all_votes.append(vote)
        game.current_votes.append(vote)
        game.phase = "voting"
        await game.save()

        mock_sio.emit.reset_mock()
        await go_to_results(game.room_id)

        game = await find_game(game.room_id)
        assert game.phase == "results"
        results_call = next(c for c in mock_sio.emit.call_args_list if c[0][0] == "game:results")
        votes_data = results_call[0][1]
        assert len(votes_data) == 1
        vote_data = votes_data[0]
        assert ai_player.user_id in (vote_data['vote_for']['user_id'], vote_data['vote_by']['user_id'])

        await game_end(game.room_id)
        mock_sio.emit.assert_any_await("game:end", ANY, to="game:victory_test")
