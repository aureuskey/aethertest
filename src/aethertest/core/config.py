"""
Configuration management for AetherTest.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AetherTest"

    # Database settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "infra_sim")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() == "true"

    @property
    def DATABASE_URL(self):
        if self.USE_SQLITE:
            return "sqlite:///./aethertest.db"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Anthropic (Claude) API settings
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Simulation settings
    DEFAULT_AGENT_COUNT: int = 100
    MAX_AGENT_COUNT: int = 2000
    DEFAULT_SIMULATION_DURATION_MINUTES: int = 30

    model_config = {
        "case_sensitive": True,
        "env_file": ".env"
    }

settings = Settings()