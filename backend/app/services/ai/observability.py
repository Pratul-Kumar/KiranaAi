import logging
import json
from datetime import datetime
from typing import Any, Dict
from app.db.supabase import get_supabase_admin_client

logger = logging.getLogger(__name__)

class AIObservability:
    """
    Handles logging, tracing, and decision auditing for AI operations.
    Useful for drift detection and model performance monitoring.
    """
    
    def __init__(self):
        self.db = get_supabase_admin_client()

    async def log_decision(
        self, 
        store_id: str, 
        pipeline_step: str, 
        input_data: Any, 
        output_data: Any, 
        confidence: float,
        reasoning: str = ""
    ):
        """Logs an AI decision to the observability table."""
        try:
            log_entry = {
                "store_id": store_id,
                "step": pipeline_step,
                "input": str(input_data),
                "output": str(output_data),
                "confidence": confidence,
                "reasoning": reasoning,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Use logger as primary, DB as persistent audit
            logger.info(f"AI_TRACE | {pipeline_step} | Conf: {confidence} | {reasoning}")
            
            # Future: Insert into Supabase 'ai_audit_logs' table
            # self.db.table("ai_audit_logs").insert(log_entry).execute()
        except Exception as e:
            logger.error(f"Failed to log AI decision: {e}")

    async def track_error(self, step: str, error: str, context: Dict[str, Any]):
        """Specialized error tracking for AI failures."""
        logger.error(f"AI_ERROR | {step} | {error} | Context: {json.dumps(context)}")
