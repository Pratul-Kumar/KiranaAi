from backend.app.inference.slm_service import SLMService
from backend.app.inference.speech_service import SpeechService
from backend.app.inference.observability import AIObservability
from backend.app.models.schemas import AIIntentResponse, IntentEnum
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
        
        # transcribe
        transcription_result = await self.speech.transcribe_audio(audio_url)
        if not transcription_result or not transcription_result.text:
            return await self._process_unknown("", "Transcription failed")
            
        # extract intent
        result = await self.slm.extract_intent_and_entities(transcription_result.text)
        
        # write trace logs
        await self.obs.log_decision(
            store_id="unknown",  # filled later in API layer
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
