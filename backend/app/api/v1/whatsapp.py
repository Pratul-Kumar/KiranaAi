from fastapi import APIRouter, Request, Header, HTTPException, Depends
from app.core.config import get_settings
from app.services.ai.ai_service import AIServiceLayer
from app.services.inventory_service import InventoryOrchestrator
from app.services.khata_service import KhataService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

def get_ai_service(): return AIServiceLayer()
def get_inventory_service(): return InventoryOrchestrator()
def get_khata_service(): return KhataService()

@router.post("/webhook")
async def whatsapp_webhook(request: Request, x_hub_signature: str = Header(None)):
    """Receives WhatsApp webhook events."""
    # 1. Verification (Simulated for MVP)
    if x_hub_signature is not None:
        logger.info(f"Signature received: {str(x_hub_signature)[:10]}...")
    
    body = await request.json()
    logger.info(f"Received WhatsApp content: {body}")
    
    # WhatsApp message structure is nested
    # entry -> changes -> value -> messages
    try:
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        from_phone = message["from"]
        msg_type = message["type"] # 'text' or 'audio'
        
        # In a real app, logic to resolve store_id from from_phone or metadata
        store_id = "test-store-id-123" # Mock
        
        if msg_type == "audio":
            audio_url = message["audio"]["url"]
            result = await get_ai_service().process_voice_message(audio_url)
        elif msg_type == "text":
            text = message["text"]["body"]
            result = await get_ai_service().process_text_message(text)
        else:
            return {"status": "ignored_type"}

        # Route based on Intent
        intent = result.get("intent")
        sku = result.get("sku")
        qty = float(result.get("quantity", 0))
        
        if intent in ["stock_update", "reorder"]:
            # +ve for stock update, -ve for sales
            change = qty if intent == "stock_update" else -qty
            response = await get_inventory_service().update_stock(sku, change, store_id)
        elif intent == "lost_sale":
            response = await get_inventory_service().log_lost_sale(sku, qty, store_id)
        elif intent == "khata_update":
            response = await get_khata_service().parse_khata_record(result["original_text"], store_id)
        else:
            response = {"status": "unknown_intent", "extracted": result}

        return {"status": "processed", "processed_result": response}

    except KeyError as e:
        logger.error(f"Invalid WhatsApp format: {e}")
        return {"status": "error", "message": "Invalid format"}

@router.get("/webhook")
async def verify_webhook(mode: str = None, token: str = None, challenge: str = None):
    """WhatsApp webhook verification."""
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
