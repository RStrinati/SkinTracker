from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import asyncio
from dotenv import load_dotenv
import logging
from bot import SkinHealthBot
from telegram import Update
import hmac
import hashlib
from urllib.parse import parse_qsl

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Skin Health Tracker Bot", version="1.0.0")

# Initialize bot
bot = SkinHealthBot()


def verify_telegram_auth(init_data: str) -> Optional[Dict[str, Any]]:
    """Verify Telegram WebApp authentication data.

    Returns the parsed data if valid, otherwise ``None``.
    """
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        hash_value = data.pop("hash", None)
        if not hash_value:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hashlib.sha256(bot.token.encode()).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if calculated_hash != hash_value:
            return None
        return data
    except Exception as e:
        logger.warning(f"Telegram auth verification failed: {e}")
        return None


async def authenticate_request(request: Request, telegram_id: int) -> Dict[str, Any]:
    """Validate Telegram auth headers and ensure user matches."""
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing auth data")
    auth_data = verify_telegram_auth(init_data)
    if not auth_data or str(telegram_id) != auth_data.get("id"):
        raise HTTPException(status_code=401, detail="Invalid auth data")
    return auth_data

@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup."""
    logger.info("Starting Skin Health Tracker Bot server...")
    await bot.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Skin Health Tracker Bot server...")
    await bot.shutdown()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Skin Health Tracker Bot is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "skin-health-tracker-bot",
        "version": "1.0.0"
    }

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram webhook requests."""
    try:
        # Get the update data from Telegram
        update_data = await request.json()
        
        # Process the update
        await bot.process_update(update_data)

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class IngredientRequest(BaseModel):
    product_name: str
    ingredients: List[str]
    conditions: List[str] = []


@app.post("/ingredients/analyze")
async def analyze_ingredients(req: IngredientRequest):
    """Analyze product ingredients against user conditions."""
    try:
        analysis = await bot.openai_service.analyze_ingredients(
            req.product_name, req.ingredients, req.conditions
        )
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"Error analyzing ingredients: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze ingredients")

@app.post("/set-webhook")
async def set_webhook():
    """Set the webhook URL for the Telegram bot."""
    try:
        base_url = os.getenv('BASE_URL')
        if not base_url:
            logger.error("BASE_URL environment variable is not set")
            raise HTTPException(status_code=500, detail="BASE_URL environment variable is not configured")

        webhook_url = f"{base_url}/webhook"
        success = await bot.set_webhook(webhook_url)
        
        if success:
            return {"message": f"Webhook set successfully to {webhook_url}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
    
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to set webhook")

@app.delete("/webhook")
async def delete_webhook():
    """Remove the webhook for the Telegram bot."""
    try:
        success = await bot.delete_webhook()
        
        if success:
            return {"message": "Webhook deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete webhook")
    
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete webhook")


@app.get("/users/{telegram_id}/logs")
async def get_user_logs(telegram_id: int, request: Request, days: int = 7):
    """Return recent logs for the specified user."""
    await authenticate_request(request, telegram_id)
    user = await bot.database.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logs = await bot.database.get_user_logs(telegram_id, days)
    return {
        "products": logs.get("products", []),
        "triggers": logs.get("triggers", []),
        "symptoms": [
            {
                "symptom_name": log.get("symptom_name"),
                "severity": log.get("severity"),
                "logged_at": log.get("logged_at"),
                "id": log.get("id"),
            }
            for log in logs.get("symptoms", [])
        ],
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
