from types import SimpleNamespace

import pytest

from app import ai
import app.util as util


@pytest.mark.asyncio
async def test_send_ai_message_exits_before_sleep_when_game_is_not_chatting(monkeypatch):
    game = SimpleNamespace(
        room_id="room-1",
        round=1,
        phase="voting",
        players=[],
        messages=[],
        messages_per_round=1,
    )

    async def fake_get_game(_game_id):
        return game

    async def fail_sleep(_seconds):
        raise AssertionError("sleep should not be used for stale AI jobs")

    monkeypatch.setattr(util, "get_game", fake_get_game)
    monkeypatch.setattr(ai.asyncio, "sleep", fail_sleep)

    await ai.send_ai_message("room-1")


@pytest.mark.asyncio
async def test_cast_ai_vote_exits_before_sleep_when_game_is_not_voting(monkeypatch):
    game = SimpleNamespace(
        room_id="room-2",
        round=1,
        phase="chatting",
        players=[],
        messages=[],
        current_votes=[],
        all_votes=[],
    )

    async def fake_get_game(_game_id):
        return game

    async def fail_sleep(_seconds):
        raise AssertionError("sleep should not be used for stale AI votes")

    monkeypatch.setattr(util, "get_game", fake_get_game)
    monkeypatch.setattr(ai.asyncio, "sleep", fail_sleep)

    await ai.cast_ai_vote("room-2")


@pytest.mark.asyncio
async def test_send_ai_message_still_posts_when_chance_gate_blocks(monkeypatch):
    ai_player = SimpleNamespace(user_id="ai-1", username="silly-goblin", is_ai=True)
    human = SimpleNamespace(user_id="human-1", username="alice", is_ai=False)
    game = SimpleNamespace(
        room_id="room-3",
        round=1,
        phase="chatting",
        topic="favorite snack",
        players=[ai_player, human],
        messages=[],
        messages_per_round=1,
        chatting_duration=20,
    )

    class FakeMessage:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        async def save(self):
            return self

    async def fake_get_game(_game_id):
        return game

    async def fake_game_save():
        return game

    async def fake_emit(_event, _payload, to=None):
        return None

    async def fake_generate_ai_reply(_game, _player):
        return "lol that sounds fun"

    monkeypatch.setattr(util, "get_game", fake_get_game)
    monkeypatch.setattr(ai, "generate_ai_reply", fake_generate_ai_reply)
    monkeypatch.setattr(ai, "Message", FakeMessage)
    monkeypatch.setattr(ai.sio, "emit", fake_emit)
    monkeypatch.setattr(ai.settings, "ai_message_chance", 0.0)
    game.save = fake_game_save

    await ai.send_ai_message("room-3")

    assert len(game.messages) == 1
    assert game.messages[0].text == "lol that sounds fun"
