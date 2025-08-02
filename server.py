from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import os
import asyncio
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)