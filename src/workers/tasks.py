import logging
from datetime import datetime, timedelta

from src.workers.celery_app import celery_app
from src.db.supabase import get_supabase_admin_client

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_whatsapp_nudge(self, customer_id: str, message_template: str) -> dict:
    """Background job to send a WhatsApp nudge to a customer."""
    import httpx
    from configs.config import get_settings

    settings = get_settings()
    db = get_supabase_admin_client()

    try:
        cust_res = db.table("customers").select("phone").eq("id", customer_id).execute()
        if not cust_res.data:
            logger.warning(f"Nudge skipped — customer {customer_id} not found.")
            return {"status": "skipped", "reason": "customer_not_found"}

        phone = cust_res.data[0]["phone"]

        if not settings.WHATSAPP_ACCESS_TOKEN:
            logger.warning("WHATSAPP_ACCESS_TOKEN not set — nudge skipped.")
            return {"status": "skipped", "reason": "no_token"}

        url = (
            f"https://graph.facebook.com/v18.0/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message_template},
        }

        response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        logger.info(f"Nudge sent to customer {customer_id} ({phone})")
        return {"status": "sent", "customer_id": customer_id}

    except Exception as exc:
        logger.error(f"Nudge failed for customer {customer_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task
def check_khata_cycles() -> int:
    """Periodic task: find overdue khata customers and trigger nudges."""
    db = get_supabase_admin_client()
    threshold_date = (datetime.utcnow() - timedelta(days=15)).isoformat()

    overdue_res = (
        db.table("khata_ledger")
        .select("customer_id, balance")
        .lt("last_payment_date", threshold_date)
        .gt("balance", 0)
        .execute()
    )

    triggered = 0
    for record in overdue_res.data:
        send_whatsapp_nudge.delay(
            record["customer_id"],
            "🔔 Friendly reminder: you have an outstanding balance at the store. Please clear it at your earliest.",
        )
        triggered += 1

    logger.info(f"check_khata_cycles: triggered {triggered} nudge(s)")
    return triggered


@celery_app.task
def check_demand_alerts() -> int:
    """Periodic task: recalculate demand scores for all active SKUs."""
    import asyncio
    from src.ml.models.demand_engine import DemandSensingEngine

    db = get_supabase_admin_client()
    engine = DemandSensingEngine()

    sku_res = db.table("skus").select("id").execute()
    triggered = 0
    for sku in sku_res.data:
        result = asyncio.run(engine.check_threshold_and_alert(sku["id"]))
        if result:
            triggered += 1

    logger.info(f"check_demand_alerts: {triggered} high-demand SKU(s) detected")
    return triggered
