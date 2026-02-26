from fastapi import APIRouter, Request, Header, HTTPException, Depends, Query
from fastapi.responses import Response
from app.core.config import get_settings
from app.services.ai.ai_service import AIServiceLayer
from app.services.inventory_service import InventoryOrchestrator
from app.services.khata_service import KhataService
from app.db.supabase import get_supabase_client
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
        
        # 2. Resolve store_id from from_phone
        db = get_supabase_client()
        store_res = db.table("stores").select("id").eq("contact_phone", from_phone).execute()
        
        if not store_res.data:
            logger.warning(f"Message from unknown number: {from_phone}. Ignoring.")
            return {"status": "unknown_sender"}
            
        store_id = store_res.data[0]["id"]
        
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
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp webhook verification."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning(f"Webhook verification failed. Mode: {hub_mode}, Token: {hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verification failed")
