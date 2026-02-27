from app.services.ai.slm_service import SLMService
from app.services.ai.speech_service import SpeechService
from app.services.ai.observability import AIObservability
from app.schemas.ai_schemas import AIIntentResponse, IntentEnum
import logging

logger = logging.getLogger(__name__)

class AIServiceLayer:
    """Production Unified service to handle voice -> intent pipeline."""
    
    def __init__(self):
        self.slm = SLMService()
        self.speech = SpeechService()
        self.obs = AIObservability()
        self.confidence_threshold = 0.6

    async def _process_unknown(self, text: str, reason: str) -> AIIntentResponse:
        return AIIntentResponse(
            intent=IntentEnum.UNKNOWN,
            confidence=0.0,
            original_text=text,
            reasoning=reason
        )

    async def process_voice_message(self, audio_url: str) -> AIIntentResponse:
        """High-level pipeline: Audio URL -> Text -> Intent JSON."""
        logger.info(f"Processing voice message from: {audio_url}")
        
        # 1. Transcribe
        transcription_result = await self.speech.transcribe_audio(audio_url)
        if not transcription_result or not transcription_result.text:
            return await self._process_unknown("", "Transcription failed")
            
        # 2. Extract Intent/Entities
        result = await self.slm.extract_intent_and_entities(transcription_result.text)
        
        # 3. Validation & Observability
        await self.obs.log_decision(
            store_id="unknown", # Store ID resolved in API layer
            pipeline_step="voice_intent_extraction",
            input_data=transcription_result.text,
            output_data=result.model_dump(),
            confidence=result.confidence,
            reasoning=result.reasoning
        )

        if result.confidence < self.confidence_threshold:
            logger.warning(f"Low AI confidence: {result.confidence} for text: {transcription_result.text}")
            
        return result

    async def process_text_message(self, text: str) -> AIIntentResponse:
        """High-level pipeline: Text -> Intent JSON."""
        logger.info(f"Processing text message: {text}")
        result = await self.slm.extract_intent_and_entities(text)
        
        await self.obs.log_decision(
            store_id="unknown",
            pipeline_step="text_intent_extraction",
            input_data=text,
            output_data=result.model_dump(),
            confidence=result.confidence,
            reasoning=result.reasoning
        )
        
        if result.confidence < self.confidence_threshold:
            logger.warning(f"Low AI confidence: {result.confidence}")
            
        return result
