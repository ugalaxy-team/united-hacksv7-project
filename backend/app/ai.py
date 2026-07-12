import datetime
import random
import uuid

from openai import AsyncOpenAI
from fastapi.encoders import jsonable_encoder

from app.config import settings
from .services import sio, scheduler
from .models import Player, Message, Vote

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

AI_MODEL = "tencent/hy3:free"

AI_MESSAGE_JOB_PREFIX = "ai_msg"
AI_VOTE_JOB_PREFIX = "ai_vote"

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

def spawn_ai_player() -> Player:
    from app.util import generate_username

    return Player(
        user_id=f"ai-{uuid.uuid4().hex}",
        username=generate_username(),
        is_ai=True,
    )


def get_ai_player(game) -> Player | None:
    for p in game.players:
        if getattr(p, "is_ai", False):
            return p
    return None


async def generate_ai_reply(game, ai_player: Player) -> str:
    history = [m for m in game.messages if m.round == game.round]
    chat_log = (
        "\n".join(f"{m.sender.username}: {m.text}" for m in history) or "(nothing yet)"
    )
    topic = getattr(game, "topic", None) or "free topic"

    prompt = (
        f"Round topic: {topic}\n\n"
        f"Chat history for this round:\n{chat_log}\n\n"
        f"Write your next chat message (as {ai_player.username})."
    )

    resp = await client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=60,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    return text.strip('"').strip()


async def schedule_ai_round(game_id: str) -> None:
    """Call right after the game transitions into the 'chatting' phase."""
    from .util import get_game

    game = await get_game(game_id)
    if not game:
        return
    ai_player = get_ai_player(game)
    if not ai_player:
        return

    n_messages = random.randint(1, max(1, game.messages_per_round))
    duration = game.chatting_duration
    slots = sorted(random.uniform(3, max(4, duration - 3)) for _ in range(n_messages))

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


async def send_ai_message(game_id: str) -> None:
    from .util import get_game, run_transition_now

    game = await get_game(game_id)
    if not game or game.phase != "chatting":
        return
    ai_player = get_ai_player(game)
    if not ai_player:
        return

    count = sum(
        1
        for m in game.messages
        if m.sender.user_id == ai_player.user_id and m.round == game.round
    )
    if count >= game.messages_per_round:
        return

    text = await generate_ai_reply(game, ai_player)

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

    await sio.emit("game:message_sent", jsonable_encoder(message), to=f"game:{game_id}")

    all_sent = all(
        sum(
            1
            for m in game.messages
            if m.sender.user_id == p.user_id and m.round == game.round
        )
        >= game.messages_per_round
        for p in game.players
    )
    if all_sent:
        run_transition_now(game_id)


async def schedule_ai_vote(game_id: str) -> None:

    from .util import get_game

    game = await get_game(game_id)
    if not game:
        return
    delay = random.uniform(game.voting_duration * 0.3, game.voting_duration * 0.8)
    scheduler.add_job(
        cast_ai_vote,
        trigger="date",
        run_date=datetime.datetime.now(tz=datetime.timezone.utc)
        + datetime.timedelta(seconds=delay),
        id=f"{AI_VOTE_JOB_PREFIX}:{game_id}:{game.round}",
        args=[game_id],
        misfire_grace_time=5,
        replace_existing=True,
    )


async def cast_ai_vote(game_id: str) -> None:
    from .util import get_game, run_transition_now

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

    if tally and random.random() < 0.7:
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

    await sio.emit("game:vote_casted", jsonable_encoder(vote), to=f"game:{game_id}")

    all_voted = all(
        any(v.vote_by.user_id == p.user_id for v in game.current_votes)
        for p in game.players
    )
    if all_voted:
        run_transition_now(game_id)
