import httpx
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class WhatsAppService:
    """
    Handles outgoing WhatsApp messages via Meta Graph API.
    """
    
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "972312215974570")
        self.version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"

    async def send_text_message(self, to: str, text: str) -> bool:
        """Sends a simple text message to a recipient."""
        if not self.access_token:
            logger.error("WHATSAPP_ACCESS_TOKEN missing in settings")
            return False

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"WhatsApp message sent to {to}")
                return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False

    async def send_template_message(self, to: str, template_name: str, language_code: str = "en_US") -> bool:
        """Sends a template message (e.g., hello_world)."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp template: {e}")
            return False

    async def send_button_message(self, to: str, text: str, buttons: list[dict]) -> bool:
        """
        Sends an interactive button message.
        buttons example: [{"id": "approve", "title": "Approve"}, {"id": "decline", "title": "Decline"}]
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Format buttons for Meta API
        formatted_buttons = []
        for btn in buttons:
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"]
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": formatted_buttons
                }
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Interactive buttons sent to {to}")
                return True
        except Exception as e:
            logger.error(f"Failed to send interactive buttons: {e}")
            return False
