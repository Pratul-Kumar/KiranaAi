import httpx
import json
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class SLMService:
    """Wrapper for Small Language Model inference (e.g., Ollama, LlamaEdge)."""
    
    def __init__(self):
        self.endpoint = settings.AI_MODEL_ENDPOINT

    async def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """Generates a response from the SLM."""
        payload = {
            "model": "mistral",  # Defaulting to mistral/llama3 for SLM usage
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for precise entity extraction
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
        except Exception as e:
            logger.error(f"Error calling SLM: {e}")
        
        return ""

    async def extract_intent_and_entities(self, text: str) -> dict:
        """Parses text to extract intent, SKU, and quantity."""
        system_prompt = (
            "You are a Kirana Store AI Assistant specialized in Hinglish (Hindi + English). "
            "Extract the following entities into a JSON object:\n"
            "- intent: (stock_update, reorder, lost_sale, khata_update)\n"
            "- sku: (name of the item)\n"
            "- quantity: (numeric value, default 1)\n"
            "- customer_name: (if mentioned, for khata_update)\n"
            "Example: '5 packet milk update' -> {intent: stock_update, sku: milk, quantity: 5}\n"
            "Output ONLY valid JSON."
        )
        prompt = f"Message: \"{text}\"\nJSON Output:"
        
        raw_response = await self.generate_response(prompt, system_prompt)
        try:
            # Simple cleanup in case of extra markdown etc
            cleaned = raw_response.strip("`").replace("json", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Failed to parse SLM JSON: {e} | Raw: {raw_response}")
            return {"intent": "unknown", "sku": None, "quantity": None}
