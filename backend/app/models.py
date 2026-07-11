from typing import Optional
from redis_om import JsonModel, Field


class Player(JsonModel, index=True):
    user_id: str = Field(index=True)
    username: str = Field(index=True)
    current_game: Optional[str] = None
    current_queue: Optional[str] = None

