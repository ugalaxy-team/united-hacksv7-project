from pydantic import model_validator, BaseModel
from pathlib import Path
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

PROJECT_PATH = Path(__file__).resolve().parents[2]
ENV_PATH = str(Path(PROJECT_PATH, ".env"))
CONFIG_PATH = str(Path(PROJECT_PATH, 'backend', "config.yml"))

class GameMode(BaseModel):
    name: str
    player_count: int # without the AI
    rounds: int
    messages_per_round: int
    chatting_duration: int = 20
    voting_duration: int = 10
    results_duration: int = 5

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH, yaml_file=CONFIG_PATH, extra="ignore", env_ignore_empty=True
    )
    # .env variables
    SECRET_KEY: str
    SQLALCHEMY_DATABASE_URI: str
    FRONTEND_URL: str
    HOST: str
    PORT: int
    REDIS_OM_URL: str
    OPENROUTER_API_KEY: str

    # config.yml
    cors_origins: list[str]

    ai_message_chance: float
    ai_vote_chance: float
    ai_response_min_delay: float
    ai_response_max_delay: float
    ai_vote_bandwagon_chance: float

    debug: bool = True

    game_modes: list[GameMode] = [
        GameMode(name='quickplay', player_count=2, rounds=1, messages_per_round=3),
        GameMode(name='standard', player_count=3, rounds=3, messages_per_round=1)
    ]

    @model_validator(mode="after")
    def _set_computed_fields(self):
        self.FRONTEND_URL.rstrip("/")
        for i in range(len(self.cors_origins)):
            self.cors_origins[i] = self.cors_origins[i].rstrip("/")
        return self

    @classmethod
    def settings_customise_sources(cls, settings_cls, env_settings, dotenv_settings, **kwargs):
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


settings = Settings()
