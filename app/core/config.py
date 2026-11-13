from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./mahadev_jyotish.db"
    secret_key: str = "dev_secret_key_change_in_production"
    allowed_origins: List[str] = ["*"]
    
    # Provider keys (kept strictly server-side, never exposed to client)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    nvidia_api_key: str | None = None
    nvidia_model: str | None = None
    swiss_ephemeris_path: str | None = None
    allow_analytical_fallback: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
