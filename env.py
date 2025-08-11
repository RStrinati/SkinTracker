from functools import lru_cache
import os
from pydantic import BaseModel, Field, ConfigDict

class Settings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    NEXT_PUBLIC_SUPABASE_URL: str = Field(..., alias='NEXT_PUBLIC_SUPABASE_URL')
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = Field(..., alias='NEXT_PUBLIC_SUPABASE_ANON_KEY')
    TELEGRAM_BOT_TOKEN: str | None = Field(default=None, alias='TELEGRAM_BOT_TOKEN')
    OPENAI_API_KEY: str | None = Field(default=None, alias='OPENAI_API_KEY')
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(default=None, alias='SUPABASE_SERVICE_ROLE_KEY')
    BASE_URL: str | None = Field(default=None, alias='BASE_URL')

@lru_cache()
def get_settings() -> Settings:
    data = {k: os.getenv(k) for k in [
        'NEXT_PUBLIC_SUPABASE_URL',
        'NEXT_PUBLIC_SUPABASE_ANON_KEY',
        'TELEGRAM_BOT_TOKEN',
        'OPENAI_API_KEY',
        'SUPABASE_SERVICE_ROLE_KEY',
        'BASE_URL',
    ]}
    return Settings(**{k: v for k, v in data.items() if v is not None})
