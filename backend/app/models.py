from typing import Optional
from redis_om import JsonModel, Field
import datetime

class Player(JsonModel, index=True):
    user_id: str = Field(index=True)
    username: str = Field(index=True)
    current_game: Optional[str] = None
    current_queue: Optional[str] = None

class Message(JsonModel, index=True):
    text: str
    created_at: datetime.datetime
    room_id: str = Field(index=True)
    round: int
    sender: Player

class Vote(JsonModel, index=True):
    vote_for: Player
    vote_by: Player

class Game(JsonModel, index=True):
    room_id: str = Field(index=True)
    round: int
    max_rounds: int
    messages_per_round: int
    phase: str # can be chatting, voting and results
    players: list[Player]
    messages: list[Message]
    # resets every round
    current_votes: list[Vote]
    all_votes: list[Vote]
    game_mode: str
    chatting_duration: int
    voting_duration: int
    results_duration: int