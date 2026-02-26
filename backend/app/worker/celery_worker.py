from celery import Celery
from app.core.config import get_settings
from app.db.supabase import get_supabase_admin_client
from datetime import datetime, timedelta
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "digital_store_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task
def send_proactive_nudge(customer_id: str, message_template: str):
    """Background job to send WhatsApp nudge messages."""
    import httpx
    
    # In a real app, resolve customer phone from ID
    # For MVP, using a test phone number
    test_phone = "919876543210" 
    
    logger.info(f"Sending nudge to CUSTOMER {customer_id} ({test_phone}): {message_template}")
    
    if not settings.WHATSAPP_ACCESS_TOKEN:
        logger.warning("WHATSAPP_ACCESS_TOKEN not set. Skipping API call.")
        return {"status": "skipped", "reason": "no_token"}

    # Mocking the Meta Graph API call
    # url = f"https://graph.facebook.com/v17.0/YOUR_PHONE_NUMBER_ID/messages"
    # headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    # payload = { ... }
    
    logger.info("WhatsApp API call simulated successfully.")
    return {"status": "nudge_sent", "customer_id": customer_id, "phone": test_phone}

@celery_app.task
def check_khata_cycles():
    """Periodic task to identify customers who haven't paid in a while."""
    db = get_supabase_admin_client()
    threshold_date = (datetime.now() - timedelta(days=15)).isoformat()
    
    overdue_res = db.table("khata_ledger").select("customer_id, balance").lt("last_payment_date", threshold_date).gt("balance", 0).execute()
    
    for record in overdue_res.data:
        cust_id = record["customer_id"]
        # Trigger async nudge
        send_proactive_nudge.delay(cust_id, "friendly_payment_reminder")
        
    return len(overdue_res.data)
