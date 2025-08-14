from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import hashlib
import hmac
import secrets
import time
import logging
import json
import sqlite3

import os
from dotenv import load_dotenv

from bot import SkinHealthBot
from api.routers.analysis import router as analysis_router

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "auth_sessions.db")
SESSION_TTL = int(os.getenv("SESSION_TTL", 24 * 60 * 60))

# Structured logging setup
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - simple wrapper
        log_record = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_record)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

# Custom filter to exclude watchfiles.main logs from error.log
class ExcludeWatchfilesFilter(logging.Filter):
    def filter(self, record):
        return record.name != "watchfiles.main"

file_handler = logging.FileHandler('error.log', encoding='utf-8')
file_handler.setFormatter(JsonFormatter())
file_handler.addFilter(ExcludeWatchfilesFilter())

root_logger = logging.getLogger()
root_logger.handlers = [handler, file_handler]
root_logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Skin Health Tracker Bot", version="1.0.0")
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(analysis_router)

bot = SkinHealthBot()

# ---------------------------------------------------------------------------
# Persistent session store using SQLite
# ---------------------------------------------------------------------------
_session_conn = sqlite3.connect(SESSION_DB_PATH, check_same_thread=False)
_session_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """
)
_session_conn.commit()


def _purge_expired_sessions() -> None:
    """Remove expired session entries from the store."""
    with _session_conn:
        _session_conn.execute(
            "DELETE FROM auth_sessions WHERE expires_at < ?",
            (int(time.time()),),
        )


def save_session(token: str, user_id: int, ttl: int = SESSION_TTL) -> None:
    """Persist a session token with an expiration time."""
    expires_at = int(time.time()) + ttl
    with _session_conn:
        _purge_expired_sessions()
        _session_conn.execute(
            "INSERT OR REPLACE INTO auth_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )


def get_user_id_from_token(token: str) -> Optional[int]:
    """Return user_id if the token is valid, otherwise ``None``."""
    cur = _session_conn.execute(
        "SELECT user_id, expires_at FROM auth_sessions WHERE token = ?",
        (token,),
    )
    row = cur.fetchone()
    if not row:
        return None
    user_id, expires_at = row
    if expires_at < int(time.time()):
        with _session_conn:
            _session_conn.execute(
                "DELETE FROM auth_sessions WHERE token = ?", (token,)
            )
        return None
    return user_id


def require_user_id(token: str) -> int:
    """Validate a session token and return the associated user ID."""
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Skin Health Tracker Bot server...")
    await bot.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Skin Health Tracker Bot server...")
    await bot.shutdown()

@app.get("/")
async def root():
    return {"message": "Skin Health Tracker Bot is running"}

@api_router.get("/health")
async def health_check():
    db_status = "ok"
    try:
        bot.database.client.table('users').select('id').limit(1).execute()
    except Exception:
        db_status = "error"
    overall = "healthy" if db_status == "ok" else "degraded"
    return {"status": overall, "services": {"database": db_status}}

class TelegramAuthRequest(BaseModel):
    id: int
    auth_date: int
    hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

@api_router.post("/auth/telegram")
async def telegram_auth(data: TelegramAuthRequest):
    try:
        bot_token = TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            raise HTTPException(status_code=500, detail="Bot token not configured")

        auth_dict = data.dict(exclude_none=True)
        received_hash = auth_dict.pop("hash")
        data_check_string = "\n".join(
            f"{k}={auth_dict[k]}" for k in sorted(auth_dict.keys())
        )
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if calculated_hash != received_hash:
            raise HTTPException(status_code=403, detail="Invalid Telegram login data")

        if time.time() - data.auth_date > 86400:
            raise HTTPException(status_code=403, detail="Authentication data is too old")

        session_token = secrets.token_urlsafe(32)
        save_session(session_token, data.id)
        return {"token": session_token}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating Telegram user: {e}")
        raise HTTPException(status_code=500, detail="Failed to authenticate")

@api_router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        update_data = await request.json()
        background_tasks.add_task(bot.process_update, update_data)
        return JSONResponse(content={"status": "accepted"})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

class IngredientRequest(BaseModel):
    product_name: str
    ingredients: List[str]
    conditions: List[str] = []

@api_router.post("/ingredients/analyze")
async def analyze_ingredients(req: IngredientRequest):
    try:
        analysis = await bot.openai_service.analyze_ingredients(
            req.product_name, req.ingredients, req.conditions
        )
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"Error analyzing ingredients: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze ingredients")

@api_router.post("/set-webhook")
async def set_webhook():
    try:
        base_url = BASE_URL
        if not base_url:
            logger.error("BASE_URL environment variable is not set")
            raise HTTPException(status_code=500, detail="BASE_URL environment variable is not configured")

        webhook_url = f"{base_url}/api/v1/webhook"
        success = await bot.set_webhook(webhook_url)

        if success:
            return {"message": f"Webhook set successfully to {webhook_url}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to set webhook")

@api_router.delete("/webhook")
async def delete_webhook():
    try:
        success = await bot.delete_webhook()
        if success:
            return {"message": "Webhook deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete webhook")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete webhook")

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    host = "127.0.0.1"
    port = 8081
    uvicorn.run("server:app", host=host, port=port, reload=True)
