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
        self._db = None
        self._whatsapp = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_supabase_admin_client()
        return self._db

    @property
    def whatsapp(self) -> WhatsAppService:
        if self._whatsapp is None:
            self._whatsapp = WhatsAppService()
        return self._whatsapp

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
