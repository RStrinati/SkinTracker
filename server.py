from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import asyncio
import hashlib
import hmac
import secrets
import time
from dotenv import load_dotenv
import logging
from bot import SkinHealthBot
from telegram import Update

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

# Simple in-memory session storage mapping tokens to Telegram IDs
sessions: Dict[str, int] = {}

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


class TelegramAuthRequest(BaseModel):
    """Schema for Telegram login authentication."""
    id: int
    auth_date: int
    hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None


@app.post("/auth/telegram")
async def telegram_auth(data: TelegramAuthRequest):
    """Authenticate a user via Telegram login data."""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            raise HTTPException(status_code=500, detail="Bot token not configured")

        auth_dict = data.dict(exclude_none=True)
        received_hash = auth_dict.pop("hash")

        # Build data-check-string
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

if __name__ == "__main__":
    import os
    import uvicorn
    host = "127.0.0.1"
    port = int(os.getenv("PORT", "8081"))
    # Pass the import string so reload works
    uvicorn.run("server:app", host=host, port=port, reload=True)

