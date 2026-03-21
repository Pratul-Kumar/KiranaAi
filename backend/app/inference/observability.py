import logging
from datetime import datetime, timezone
from typing import Any, Dict

from backend.app.db.supabase import get_supabase_admin_client_safe

logger = logging.getLogger(__name__)


class AIObservability:
    """Handles logging, tracing, and decision auditing for AI operations."""

    def __init__(self) -> None:
        self.db = None

    def _get_db(self):
        if self.db is None:
            self.db = get_supabase_admin_client_safe()
        return self.db

    async def log_decision(
        self,
        store_id: str,
        pipeline_step: str,
        input_data: Any,
        output_data: Any,
        confidence: float,
        reasoning: str = "",
    ) -> None:
        logger.info(f"AI_TRACE | {pipeline_step} | conf={confidence:.2f} | {reasoning}")
        db = self._get_db()
        if db is None:
            logger.warning("Skipping AI audit persistence because Supabase is unavailable")
            return
        try:
            db.table("ai_audit_logs").insert({
                "store_id": store_id,
                "step": pipeline_step,
                "input": str(input_data),
                "output": str(output_data),
                "confidence": confidence,
                "reasoning": reasoning,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as exc:
            logger.error(f"Failed to persist AI audit log: {exc}")

    async def track_error(self, step: str, error: str, context: Dict[str, Any]) -> None:
        import json
        logger.error(f"AI_ERROR | {step} | {error} | context={json.dumps(context)}")
