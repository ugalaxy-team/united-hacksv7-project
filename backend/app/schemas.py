import datetime

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    username: str
    id: str


class PlayerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    user_id: str
    username: str


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    text: str
    created_at: datetime.datetime
    room_id: str
    round: int
    sender: PlayerPublic


class VotePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    vote_for: PlayerPublic
    vote_by: PlayerPublic


class GamePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    room_id: str
    round: int
    max_rounds: int
    messages_per_round: int
    phase: str
    topic: str
    players: list[PlayerPublic]
    messages: list[MessagePublic]
    current_votes: list[VotePublic]
    all_votes: list[VotePublic]
    game_mode: str
    chatting_duration: int
    voting_duration: int
    results_duration: int
