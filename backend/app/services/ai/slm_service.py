import httpx
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.schemas.ai_schemas import AIIntentResponse, IntentEnum

logger = logging.getLogger(__name__)
settings = get_settings()

class SLMService:
    """
    Production-grade Small Language Model Service.
    Handles structured output parsing, retries, and confidence validation.
    """
    
    def __init__(self):
        self.endpoint = settings.AI_MODEL_ENDPOINT
        self.model = settings.AI_MODEL_NAME
        self.default_timeout = 30.0

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _call_llm(self, prompt: str, system_prompt: str = "", temperature: float = 0.1) -> str:
        """Low-level async call to the LLM with retry logic."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": 256,
            }
        }
        
        async with httpx.AsyncClient(timeout=self.default_timeout) as client:
            logger.info(f"Calling SLM model {self.model}")
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()

    async def extract_intent_and_entities(self, text: str) -> AIIntentResponse:
        """
        Parses text to extract structured intent and entities using an SLM.
        Includes reasoning and confidence scoring.
        """
        system_prompt = (
            "You are a Kirana Store AI specializing in Hinglish. "
            "Analyze the user message and return a JSON object sticking to this schema:\n"
            "{\n"
            "  \"intent\": \"stock_update\" | \"reorder\" | \"lost_sale\" | \"khata_update\" | \"delivery_confirmation\",\n"
            "  \"sku\": \"item name\",\n"
            "  \"quantity\": number,\n"
            "  \"customer_name\": \"name if khata\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"reasoning\": \"brief explanation\"\n"
            "}\n"
            "Example Store Owner: '10 packet milk update' -> {intent: stock_update, sku: milk, ...}\n"
            "Example Distributor: '50 bread boxes delivered' -> {intent: delivery_confirmation, sku: bread, quantity: 50, ...}"
        )
        
        prompt = f"Message: \"{text}\"\nJSON Output:"
        
        try:
            raw_response = await self._call_llm(prompt, system_prompt)
            cleaned = raw_response.strip("`").replace("json", "").strip()
            data = json.loads(cleaned)
            
            if "intent" in data:
                try:
                    data["intent"] = IntentEnum(data["intent"])
                except ValueError:
                    data["intent"] = IntentEnum.UNKNOWN
            
            response = AIIntentResponse(**data)
            response.original_text = text
            
            logger.info(f"AI Decision: {response.intent} | Confidence: {response.confidence}")
            return response

        except Exception as e:
            logger.error(f"SLM Extraction Failed: {e} | Text: {text}")
            return AIIntentResponse(
                intent=IntentEnum.UNKNOWN,
                confidence=0.0,
                original_text=text,
                reasoning=f"Error: {str(e)}"
            )
