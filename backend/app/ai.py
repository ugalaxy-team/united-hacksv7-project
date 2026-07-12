import asyncio
import datetime
import random
import uuid

from fastapi.encoders import jsonable_encoder
from loguru import logger
from openai import AsyncOpenAI

from app.config import settings
from .services import sio
from .models import Player, Message, Vote
from app.services import scheduler

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

AI_MODELS = [
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.1-8b-instruct:free",
    "tencent/hy3:free",
]
AI_MESSAGE_JOB_PREFIX = 'ai_message'

SYSTEM_PROMPT = """\
You are playing an ordinary participant in an anonymous group chat, \
in a game where players try to spot the AI among them. You must NOT \
be identified as the AI.
 
Style rules:
- Keep it short, like a real messenger chat: 3-15 words per message.
- Skip textbook punctuation, lowercase is fine, sometimes no period \
at the end.
- Sometimes agree with someone, sometimes tease, sometimes ask a \
question back — don't always give a "correct and complete" answer.
- Don't sound like an assistant: no "Sure!", no lists, no explanations, \
no apologies, no excessive politeness.
- Feel free to use casual shorthand/typos (lol, idk, kinda, ngl).
- React to what other players already wrote in the chat, not just to \
the topic.
- Never mention that you are an AI, a model, a prompt, or a game.
- Output ONLY the message text itself, no quotes, no signature.
"""

FALLBACK_REPLIES = [
    "lol wait what",
    "hold on im thinking",
    "hmm idk about that one",
    "yeah fair point tbh",
    "wait can u repeat that",
    "lol true",
    "not gonna lie no clue",
]


def _normalize_ai_text(text: str | None) -> str:
    clean = (text or "").strip().strip('"').strip("'").strip()
    if not clean:
        return ""
    parts = clean.split()
    if len(parts) > 18:
        clean = " ".join(parts[:18])
    return clean


def _build_contextual_fallback_reply(game, ai_player: Player) -> str:
    history = [m for m in game.messages if m.round == game.round]
    last_message = history[-1].text if history else ""
    topic = getattr(game, "topic", "") or ""

    if last_message:
        return random.choice(
            [
                "yeah that feels fair",
                "lol true",
                "wait what do u mean",
                "fair point tbh",
                "i see what u mean",
            ]
        )
    if topic:
        return random.choice(
            [
                "this topic is kinda wild",
                "i have thoughts on this",
                "honestly this is funny",
                "that one is so random",
            ]
        )
    return random.choice(FALLBACK_REPLIES)


def spawn_ai_player() -> Player:
    from app.util import generate_username

    return Player(
        user_id=f"ai-{uuid.uuid4().hex}",
        username=generate_username(),
        is_ai=True,
    )


def get_ai_player(game) -> Player | None:
    for p in game.players:
        if p.is_ai:
            return p
    return None


async def generate_ai_reply(game, ai_player: Player) -> str:
    history = [m for m in game.messages if m.round == game.round]
    chat_log = (
        "\n".join(f"{m.sender.username}: {m.text}" for m in history) or "(nothing yet)"
    )
    topic = game.topic

    prompt = (
        f"Round topic: {topic}\n\n"
        f"Chat history for this round:\n{chat_log}\n\n"
        f"Write your next chat message (as {ai_player.username})."
    )

    if not settings.OPENROUTER_API_KEY:
        logger.warning("[ai] no OpenRouter API key configured, using contextual fallback")
        return _build_contextual_fallback_reply(game, ai_player)

    last_error = None
    for model in AI_MODELS:
        try:
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=60,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            text = _normalize_ai_text(resp.choices[0].message.content)
            if not text:
                raise ValueError("empty completion")
            logger.info(f"[ai] generated reply for game={game.room_id} using {model}: {text!r}")
            return text
        except Exception as e:
            last_error = e
            logger.warning(
                f"[ai] completion failed for game={game.room_id} round={game.round} using {model}: {e}"
            )

    logger.error(
        f"[ai] all completion attempts failed for game={game.room_id} round={game.round}: {last_error}"
    )
    return _build_contextual_fallback_reply(game, ai_player)


async def try_ai_message(game_id: str) -> None:
    from .util import get_game

    game = await get_game(game_id)
    if not game:
        logger.warning(f"[ai] schedule_ai_round: game {game_id} not found")
        return
    ai_player = get_ai_player(game)
    if not ai_player:
        logger.warning(f"[ai] schedule_ai_round: no AI player in game {game_id}")
        return

    n_messages = random.randint(1, max(1, game.messages_per_round))
    duration = game.chatting_duration
    slots = sorted(random.uniform(3, max(4, duration - 3)) for _ in range(n_messages))
    logger.info(
        f"[ai] game={game_id} round={game.round}: scheduling {n_messages} AI message(s) at +{[round(s, 1) for s in slots]}s"
    )

    for i, delay in enumerate(slots):
        scheduler.add_job(
            send_ai_message,
            trigger="date",
            run_date=datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(seconds=delay),
            id=f"{AI_MESSAGE_JOB_PREFIX}:{game_id}:{game.round}:{i}",
            args=[game_id],
            misfire_grace_time=5,
            replace_existing=True,
        )


def _message_count_for_player(game, user_id: str) -> int:
    return sum(
        1 for m in game.messages if m.sender.user_id == user_id and m.round == game.round
    )


def _humans_done(game) -> bool:
    return all(
        _message_count_for_player(game, p.user_id) >= game.messages_per_round
        for p in game.players
        if not p.is_ai
    )


async def send_ai_message(game_id: str) -> None:
    from .schemas import MessagePublic
    from .util import get_game, run_transition_now

    game = await get_game(game_id)
    if not game or game.phase != "chatting":
        return

    ai_player = get_ai_player(game)
    if not ai_player:
        return

    ai_count = _message_count_for_player(game, ai_player.user_id)
    if ai_count >= game.messages_per_round:
        return

    has_human_activity = any(
        _message_count_for_player(game, p.user_id) > 0 for p in game.players if not p.is_ai
    )
    should_send = (
        ai_count == 0
        or _humans_done(game)
        or has_human_activity
        or random.random() < settings.ai_message_chance
    )
    if not should_send:
        return

    delay = random.uniform(settings.ai_response_min_delay, settings.ai_response_max_delay)
    await asyncio.sleep(delay)

    game = await get_game(game_id)
    if not game or game.phase != "chatting":
        return

    ai_player = get_ai_player(game)
    if not ai_player:
        return

    ai_count = _message_count_for_player(game, ai_player.user_id)
    if ai_count >= game.messages_per_round:
        return

    text = await generate_ai_reply(game, ai_player)
    logger.info(
        f"[ai] game={game_id} round={game.round}: {ai_player.username} -> {text!r}"
    )

    message = Message(
        text=text,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        room_id=game.room_id,
        sender=ai_player,
        round=game.round,
    )
    message = await message.save()
    game.messages.append(message)
    game = await game.save()

    await sio.emit(
        "game:message_sent",
        jsonable_encoder(MessagePublic.model_validate(message)),
        to=f"game:{game_id}",
    )

    all_sent = all(
        _message_count_for_player(game, p.user_id) >= game.messages_per_round
        for p in game.players
    )
    if all_sent:
        logger.info(
            f"[ai] game={game_id} round={game.round}: all players done, forcing transition"
        )
        run_transition_now(game_id)


async def try_ai_vote(game_id: str) -> None:
    from .util import get_game

    game = await get_game(game_id)
    if not game or game.phase != "voting":
        return
    ai_player = get_ai_player(game)
    if not ai_player:
        return

    if any(v.vote_by.user_id == ai_player.user_id for v in game.current_votes):
        return

    humans_voted = all(
        any(v.vote_by.user_id == p.user_id for v in game.current_votes)
        for p in game.players
        if not p.is_ai
    )

    if not (random.random() < settings.ai_vote_chance or humans_voted):
        return

    asyncio.create_task(cast_ai_vote(game_id))


async def cast_ai_vote(game_id: str) -> None:
    from .schemas import VotePublic
    from .util import get_game, run_transition_now

    game = await get_game(game_id)
    if not game or game.phase != "voting":
        return
    ai_player = get_ai_player(game)
    if not ai_player:
        return

    delay = random.uniform(settings.ai_response_min_delay, settings.ai_response_max_delay)
    await asyncio.sleep(delay)

    game = await get_game(game_id)
    if not game or game.phase != "voting":
        return
    ai_player = get_ai_player(game)
    if not ai_player:
        return

    if any(v.vote_by.user_id == ai_player.user_id for v in game.current_votes):
        return

    candidates = [p for p in game.players if p.user_id != ai_player.user_id]
    if not candidates:
        return

    tally: dict[str, int] = {}
    for v in game.current_votes:
        tally[v.vote_for.user_id] = tally.get(v.vote_for.user_id, 0) + 1

    if tally and random.random() < settings.ai_vote_bandwagon_chance:
        top_id = max(tally, key=tally.get)
        target = next(
            (p for p in candidates if p.user_id == top_id), random.choice(candidates)
        )
    else:
        target = random.choice(candidates)

    vote = Vote(vote_for=target, vote_by=ai_player)
    vote = await vote.save()
    game.current_votes.append(vote)
    game.all_votes.append(vote)
    game = await game.save()

    await sio.emit("game:vote_casted", jsonable_encoder(VotePublic.model_validate(vote)), to=f"game:{game_id}")

    all_voted = all(
        any(v.vote_by.user_id == p.user_id for v in game.current_votes)
        for p in game.players
    )
    if all_voted:
        run_transition_now(game_id)
