import logging
from typing import Optional

import httpx

from configs.config import get_settings
from backend.app.db.supabase import get_supabase_admin_client
from backend.app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    def __init__(self) -> None:
        self.db = get_supabase_admin_client()
        self.whatsapp = WhatsAppService()

    async def send_broadcast(
        self,
        message: str,
        store_ids: Optional[list[str]] = None,
    ) -> dict:
        if store_ids:
            res = self.db.table("stores").select("contact_phone, name").in_("id", store_ids).execute()
        else:
            res = self.db.table("stores").select("contact_phone, name").execute()

        stores = res.data or []
        sent, failed = 0, 0

        for store in stores:
            phone = store.get("contact_phone")
            if not phone:
                continue
            success = await self.whatsapp.send_text_message(phone, message)
            if success:
                sent += 1
            else:
                failed += 1
                logger.warning(f"Broadcast failed for store: {store.get('name')}")

        logger.info(f"Broadcast complete — sent: {sent}, failed: {failed}")
        return {"sent": sent, "failed": failed, "total": len(stores)}
