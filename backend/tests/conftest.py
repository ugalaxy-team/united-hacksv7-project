import os
os.environ["REDIS_OM_URL"] = "redis://@localhost:6378/0"

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest_asyncio.fixture(scope="session", autouse=True)
async def run_migrator():
    from aredis_om import Migrator
    await Migrator().run()
    yield


@pytest.fixture(autouse=True)
def reset_scheduler():
    from app.services import scheduler
    scheduler._pending_jobs.clear()
    yield


@pytest.fixture(autouse=True)
async def clear_redis():
    """Delete test data keys before and after each test (preserves indexes)."""
    from app.services import redis
    from app.models import Player, Game, Vote, Message
    prefixes = [
        Player.Meta.model_key_prefix,
        Game.Meta.model_key_prefix,
        Vote.Meta.model_key_prefix,
        Message.Meta.model_key_prefix,
        "queue", "game",
    ]
    keys = []
    for prefix in prefixes:
        if prefix in ("queue", "game"):
            async for key in redis.scan_iter(f"{prefix}:*"):
                keys.append(key)
        else:
            async for key in redis.scan_iter(f":{prefix}:*"):
                keys.append(key)
    for static_key in ("apscheduler.jobs", "apscheduler.run_times"):
        if await redis.exists(static_key):
            keys.append(static_key)
    if keys:
        await redis.delete(*keys)
    yield
    keys = []
    for prefix in prefixes:
        if prefix in ("queue", "game"):
            async for key in redis.scan_iter(f"{prefix}:*"):
                keys.append(key)
        else:
            async for key in redis.scan_iter(f":{prefix}:*"):
                keys.append(key)
    for static_key in ("apscheduler.jobs", "apscheduler.run_times"):
        if await redis.exists(static_key):
            keys.append(static_key)
    if keys:
        await redis.delete(*keys)


@pytest.fixture
def mock_sio():
    mock = MagicMock()
    mock.emit = AsyncMock()
    mock.enter_room = AsyncMock()
    mock.leave_room = AsyncMock()
    mock.close_room = AsyncMock()
    mock.disconnect = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def patch_sio(mock_sio):
    import app.services
    import app.util
    import app.websockets
    orig = (app.services.sio, app.util.sio, app.websockets.sio)
    app.services.sio = mock_sio
    app.util.sio = mock_sio
    app.websockets.sio = mock_sio
    yield
    app.services.sio, app.util.sio, app.websockets.sio = orig


@pytest.fixture(autouse=True)
def clear_state():
    from app import app
    app.state.user_websocket_sessions.clear()


@pytest.fixture
def sid():
    return "test_sid_001"


@pytest.fixture
def sid2():
    return "test_sid_002"


@pytest.fixture
def sid3():
    return "test_sid_003"
