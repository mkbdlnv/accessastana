"""Runtime settings from environment variables (12-factor). See .env.example."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings from ACCESSASTANA_* environment variables and .env."""

    model_config = SettingsConfigDict(env_prefix="ACCESSASTANA_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://accessastana:accessastana@localhost:5432/accessastana"
    # Root of config/ and data/ (the repo root locally, /app in Docker).
    project_root: Path = Path(__file__).resolve().parents[2]
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    # Upper bound of on-demand computations, protects a small EC2 instance.
    optimize_max_k: int = 20
    scenario_max_facilities: int = 50

    @property
    def config_dir(self) -> Path:
        """Directory with the YAML config."""
        return self.project_root / "config"


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings (cached)."""
    return Settings()
