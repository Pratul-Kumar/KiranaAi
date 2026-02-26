from app.services.ai.slm_service import SLMService
from app.services.ai.speech_service import SpeechService
import logging

logger = logging.getLogger(__name__)

class AIServiceLayer:
    """Unified service to handle voice -> intent pipeline."""
    
    def __init__(self):
        self.slm = SLMService()
        self.speech = SpeechService()

    async def process_voice_message(self, audio_url: str) -> dict:
        """High-level pipeline: Audio URL -> Text -> Intent JSON."""
        logger.info(f"Processing voice message from: {audio_url}")
        
        # 1. Transcribe
        text = await self.speech.transcribe_audio(audio_url)
        if not text:
            return {"error": "Transcription failed"}
            
        # 2. Extract Intent/Entities
        result = await self.slm.extract_intent_and_entities(text)
        result["original_text"] = text
        
        return result

    async def process_text_message(self, text: str) -> dict:
        """High-level pipeline: Text -> Intent JSON."""
        logger.info(f"Processing text message: {text}")
        result = await self.slm.extract_intent_and_entities(text)
        result["original_text"] = text
        return result
