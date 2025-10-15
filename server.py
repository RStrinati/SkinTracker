from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, APIRouter
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
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

# Import routers with error handling for Railway deployment
try:
    from api.routers.analysis import router as analysis_router
    ANALYSIS_ROUTER_AVAILABLE = True
    print("Analysis router loaded successfully")
except ImportError as e:
    print(f"Analysis router not available (expected in Railway deployment): {e}")
    analysis_router = APIRouter()  # Empty router
    ANALYSIS_ROUTER_AVAILABLE = False

try:
    from api.timeline import router as timeline_router
    TIMELINE_ROUTER_AVAILABLE = True
    print("Timeline router loaded successfully")
except ImportError as e:
    print(f"Timeline router not available: {e}")
    timeline_router = APIRouter()  # Empty router
    TIMELINE_ROUTER_AVAILABLE = False

from telegram import Update

# Load environment variables from .env file (for local development)
if not os.getenv("CLOUDFLARE_WORKERS"):
    load_dotenv()

# Import Cloudflare database adapter
try:
    from cloudflare_database import get_cloudflare_db
    CLOUDFLARE_MODE = True
except ImportError:
    CLOUDFLARE_MODE = False

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "auth_sessions.db")
SESSION_TTL = int(os.getenv("SESSION_TTL", 24 * 60 * 60))

# Railway-specific configuration
PORT = int(os.getenv("PORT", 8080))  # Railway defaults to 8080
HOST = os.getenv("HOST", "0.0.0.0")

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

# Railway-safe logging - no file handler
try:
    file_handler = logging.FileHandler('error.log', encoding='utf-8')
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(ExcludeWatchfilesFilter())
    handlers = [handler, file_handler]
except PermissionError:
    # Railway doesn't allow file writing - use only console
    handlers = [handler]

root_logger = logging.getLogger()
root_logger.handlers = handlers
root_logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Initialize API router
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(analysis_router)

# Initialize bot with error handling
try:
    bot = SkinHealthBot()
    logger.info("Bot instance created successfully")
except Exception as e:
    logger.error(f"Failed to create bot instance: {e}")
    # Create a minimal bot object to prevent crashes
    class MockBot:
        def __init__(self):
            self.database = None
        async def initialize(self): pass
        async def shutdown(self): pass
    bot = MockBot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Starting Skin Health Tracker Bot server...")
        logger.info(f"Environment check - Bot token available: {bool(TELEGRAM_BOT_TOKEN)}")
        logger.info(f"Environment check - Base URL: {BASE_URL}")
        logger.info(f"Components - Analysis router: {ANALYSIS_ROUTER_AVAILABLE}")
        logger.info(f"Components - Timeline router: {TIMELINE_ROUTER_AVAILABLE}")
        logger.info(f"Environment - Railway: {bool(os.getenv('RAILWAY_ENVIRONMENT'))}")
        logger.info(f"Port configuration: {PORT}")
        
        # Only initialize bot if we have required environment variables
        if TELEGRAM_BOT_TOKEN:
            await bot.initialize()
            logger.info("Bot initialized successfully")
            logger.info(f"✅ READY TO ACCEPT TRAFFIC ON PORT {PORT}")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set - running in limited mode")
            logger.info(f"✅ READY TO ACCEPT TRAFFIC ON PORT {PORT} (limited mode)")
            
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Don't crash the server, just log the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down Skin Health Tracker Bot server...")
    await bot.shutdown()

app = FastAPI(title="Skin Health Tracker Bot", version="1.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Persistent session store - with Cloudflare D1 support
# ---------------------------------------------------------------------------

# Check if we're running in Cloudflare Workers
if CLOUDFLARE_MODE and os.getenv("CLOUDFLARE_WORKERS"):
    # Use Cloudflare D1 database
    cloudflare_db = get_cloudflare_db()
    
    async def save_session(token: str, user_id: int, ttl: int = SESSION_TTL) -> None:
        """Persist a session token with an expiration time in D1."""
        expires_at = int(time.time()) + ttl
        await cloudflare_db.create_session(token, user_id, expires_at)
    
    async def get_user_id_from_token(token: str) -> Optional[int]:
        """Return user_id if the token is valid from D1, otherwise None."""
        session = await cloudflare_db.get_session(token)
        return session['user_id'] if session else None
    
    async def require_user_id(token: str) -> int:
        """Validate a session token and return the associated user ID from D1."""
        user_id = await get_user_id_from_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_id
    
else:
    # Use in-memory SQLite database for Railway compatibility
    try:
        # Try to use file-based database for local development
        if not os.getenv("RAILWAY_ENVIRONMENT"):
            _session_conn = sqlite3.connect(SESSION_DB_PATH, check_same_thread=False)
        else:
            # Use in-memory database for Railway deployment
            _session_conn = sqlite3.connect(":memory:", check_same_thread=False)
            logger.info("Using in-memory session storage for Railway deployment")
    except Exception as e:
        # Fallback to in-memory database if file creation fails
        logger.warning(f"Failed to create file database, using in-memory: {e}")
        _session_conn = sqlite3.connect(":memory:", check_same_thread=False)
    
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

@app.get("/")
async def root():
    return {"message": "Skin Health Tracker Bot is running - FastAPI Lifespan Update Applied"}

@app.get("/health")
async def health_check_root():
    """Simplified health check for Railway compatibility."""
    return {"status": "healthy", "timestamp": time.time(), "port": PORT}

@api_router.get("/health")
async def health_check():
    """Detailed health check with database status."""
    db_status = "ok"
    try:
        bot.database.client.table('users').select('id').limit(1).execute()
    except Exception as e:
        logger.warning(f"Health check database query failed: {e}")
        db_status = "error"
    overall = "healthy" if db_status == "ok" else "degraded"
    return {
        "status": overall, 
        "services": {"database": db_status},
        "port": PORT,
        "timestamp": time.time()
    }

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
        
        # Handle both async (Cloudflare) and sync (local) save_session
        if CLOUDFLARE_MODE and os.getenv("CLOUDFLARE_WORKERS"):
            await save_session(session_token, data.id)
        else:
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
        started = time.perf_counter()
        update_data = await request.json()
        update_id = update_data.get("update_id")
        
        # Enhanced logging to see what type of update we're receiving
        update_type = "unknown"
        if "message" in update_data:
            message = update_data["message"]
            if "photo" in message:
                update_type = "photo"
                logger.info("[WEBHOOK] Photo upload received - update_id=%s", update_id)
            elif "text" in message:
                update_type = "text"
                logger.info("[WEBHOOK] Text message received - update_id=%s", update_id)
            else:
                update_type = "other_message"
                logger.info("[WEBHOOK] Other message type received - update_id=%s", update_id)
        elif "callback_query" in update_data:
            update_type = "callback"
            logger.info("[WEBHOOK] Callback query received - update_id=%s", update_id)
        
        background_tasks.add_task(process_update_safe, update_data)
        took = (time.perf_counter() - started) * 1000
        logger.info("Webhook ack: update_id=%s type=%s in %.1fms", update_id, update_type, took)
        return JSONResponse(content={"status": "accepted"})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_update_safe(update_data: dict):
    from telegram.error import RetryAfter, BadRequest

    update = Update.de_json(update_data, bot.bot)
    chat_id = update.effective_chat.id if update.effective_chat else None
    update_id = update.update_id
    started = time.perf_counter()
    
    # Log what type of update we're processing
    if update.message and update.message.photo:
        logger.info("[UPDATE] Starting photo processing - update_id=%s chat_id=%s", update_id, chat_id)
    elif update.message and update.message.text:
        logger.info("[UPDATE] Processing text message - update_id=%s chat_id=%s", update_id, chat_id)
    else:
        logger.info("[UPDATE] Processing other update type - update_id=%s chat_id=%s", update_id, chat_id)
    
    try:
        await bot.application.process_update(update)
        logger.info("[UPDATE] Successfully processed - update_id=%s", update_id)
    except RetryAfter as e:
        logger.warning("Rate limited: sleeping %.2fs", e.retry_after)
        await asyncio.sleep(e.retry_after)
        try:
            await bot.process_update(update_data)
            logger.info("[UPDATE] Successfully processed after retry - update_id=%s", update_id)
        except Exception:
            logger.exception("Failed after RetryAfter")
    except BadRequest:
        logger.exception("BadRequest in process_update")
        if chat_id:
            try:
                await bot.bot.send_message(
                    chat_id=chat_id,
                    text="I saved your photo but couldn’t format the message. I’ll improve this shortly.",
                )
            except Exception:
                logger.exception("Failed to notify user of BadRequest")
    except Exception:
        logger.exception("Unhandled error in process_update")
        if chat_id:
            try:
                await bot.bot.send_message(
                    chat_id=chat_id,
                    text="I saved your photo, but processing hit an error. I’ll take a look and update you.",
                )
            except Exception:
                logger.exception("Failed to notify user of error")
    finally:
        took = (time.perf_counter() - started) * 1000
        logger.info("Processed update %s in %.1fms", update.update_id, took)

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
app.include_router(timeline_router)

# Mount static files for the timeline web app
app.mount("/public", StaticFiles(directory="public"), name="public")

# Timeline page route
@app.get("/timeline")
async def timeline_page():
    """Serve the timeline web app."""
    from fastapi.responses import FileResponse
    return FileResponse("public/timeline.html")

if __name__ == "__main__":
    import uvicorn
    try:
        # This will only run in local development
        # Railway will use uvicorn command from railway.json
        logger.info(f"Starting server on {HOST}:{PORT}")
        uvicorn.run("server:app", host=HOST, port=PORT, reload=False, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
