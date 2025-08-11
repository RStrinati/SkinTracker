from functools import lru_cache
import os
from pydantic import BaseModel, Field, ConfigDict, ValidationError

class Settings(BaseModel):
    """Application settings loaded from environment variables.

    All fields are required to avoid runtime errors caused by missing
    configuration.  Validation is performed at startup so the application
    fails fast with a clear message if any variables are absent.
    """

    model_config = ConfigDict(populate_by_name=True)

    NEXT_PUBLIC_SUPABASE_URL: str = Field(..., alias="NEXT_PUBLIC_SUPABASE_URL")
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = Field(..., alias="NEXT_PUBLIC_SUPABASE_ANON_KEY")
    TELEGRAM_BOT_TOKEN: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY: str = Field(..., alias="OPENAI_API_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
    BASE_URL: str = Field(..., alias="BASE_URL")

@lru_cache()
def get_settings() -> Settings:
    """Load and validate settings from the environment."""

    keys = [
        "NEXT_PUBLIC_SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "BASE_URL",
    ]
    data = {k: os.getenv(k) for k in keys}
    try:
        return Settings(**data)
    except ValidationError as e:  # pragma: no cover - trivial
        missing = ", ".join(err["loc"][0] for err in e.errors())
        raise RuntimeError(
            f"Missing required environment variables: {missing}"
        ) from e
