from app.db.supabase import get_supabase_admin_client
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import math

logger = logging.getLogger(__name__)

class DemandSensingEngine:
    """
    Production Demand Sensing Engine.
    Replaces static weights with time-decayed scoring and seasonality mocks.
    """
    
    def __init__(self):
        self.db = get_supabase_admin_client()

    def _calculate_time_decay(self, timestamp_str: str, half_life_days: int = 7) -> float:
        """Applies exponential time decay to signals."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            age_days = (datetime.utcnow().replace(tzinfo=dt.tzinfo) - dt).total_seconds() / 86400.0
            return math.exp(-0.693 * age_days / half_life_days)
        except:
            return 1.0

    async def calculate_demand_score(self, sku_id: str) -> float:
        """
        Enhanced DemandScore:
        DemandScore = (SalesVelocity * W1) + (DecayedLostSales * W2) + (Seasonality * W3)
        """
        # 1. Sales Velocity (Mock: Transactions in last 7 days)
        # In production: SELECT COUNT(*) FROM transactions WHERE ...
        velocity = 0.8 
        
        # 2. Lost Requests with Time Decay
        lost_sales_res = self.db.table("lost_sales").select("detected_at, requested_qty").eq("sku_id", sku_id).execute()
        
        lost_score = 0.0
        for entry in lost_sales_res.data:
            decay = self._calculate_time_decay(entry["detected_at"])
            lost_score += (entry["requested_qty"] * decay)
            
        lost_score_norm = min(lost_score / 10.0, 1.0) # Normalize
        
        # 3. External Factors (Seasonality & Weather)
        # Mocking seasonal peak for certain SKUs (e.g., cold drinks in summer)
        seasonality_impact = 0.2 # Placeholder
        
        # Weighted Final Score
        W_VELOCITY = 0.4
        W_LOST = 0.4
        W_SEASON = 0.2
        
        demand_score = (velocity * W_VELOCITY) + (lost_score_norm * W_LOST) + (seasonality_impact * W_SEASON)
        demand_score = round(min(demand_score, 5.0), 2) # Cap at 5.0
        
        # Record Signal for Traceability
        self.db.table("demand_signals").insert({
            "sku_id": sku_id,
            "demand_score": demand_score,
            "velocity": velocity,
            "external_factors": {
                "lost_score_dec": lost_score,
                "seasonality": seasonality_impact,
                "calculated_at": datetime.utcnow().isoformat()
            }
        }).execute()
        
        return demand_score

    async def check_threshold_and_alert(self, sku_id: str, threshold: float = 2.5) -> bool:
        """Triggers reorder optimization/nudge if demand > threshold."""
        score = await self.calculate_demand_score(sku_id)
        
        if score > threshold:
            logger.warning(f"HIGH DEMAND DETECTED: SKU {sku_id} | Score: {score}")
            # In production: Trigger Celery task for reorder recommendation
            return True
        return False
