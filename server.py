from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import hashlib
import hmac
import secrets
import time
import logging
import json

from bot import SkinHealthBot
from env import get_settings

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
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="Skin Health Tracker Bot", version="1.0.0")
api_router = APIRouter(prefix="/api/v1")

bot = SkinHealthBot()

sessions: Dict[str, int] = {}

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
        bot_token = settings.TELEGRAM_BOT_TOKEN
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
        sessions[session_token] = data.id
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
        base_url = settings.BASE_URL
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
