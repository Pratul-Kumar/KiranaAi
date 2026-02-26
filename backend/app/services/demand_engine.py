from app.db.supabase import get_supabase_admin_client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DemandSensingEngine:
    """
    Implements the DemandScore formula:
    DemandScore = SalesVelocity + LostRequests + FestivalImpact + WeatherImpact + KhataCycleProbability
    """
    
    def __init__(self):
        self.db = get_supabase_admin_client()

    async def calculate_demand_score(self, sku_id: str) -> float:
        """
        Calculates and updates the demand score for a particular SKU.
        """
        # Fetch SKU and external factors (mocking these for MVP)
        # In a real app, these would come from Weather/Festival APIs or historical DB logs
        
        # 1. SalesVelocity (calculated from transactions)
        velocity = 0.5 
        
        # 2. LostRequests (from lost_sales table)
        lost_sales_response = self.db.table("lost_sales").select("*").eq("sku_id", sku_id).execute()
        lost_count = len(lost_sales_response.data)
        lost_score = lost_count * 0.2
        
        # 3. Festival Impact (e.g., Holi/Diwali +0.8)
        festival_impact = 0.0
        
        # 4. Weather Impact (e.g., Rainy day +0.5 for tea/snacks)
        weather_impact = 0.0
        
        # 5. KhataCycleProbability (Purchase frequency logic)
        khata_score = 0.1
        
        demand_score = velocity + lost_score + festival_impact + weather_impact + khata_score
        
        # Save to DB
        self.db.table("demand_signals").insert({
            "sku_id": sku_id,
            "demand_score": demand_score,
            "velocity": velocity,
            "external_factors": {"weather": "Sunny", "festival": "None"}
        }).execute()
        
        return demand_score

    async def check_threshold_and_alert(self, sku_id: str, threshold: float = 2.0) -> bool:
        """Cross-checks demand score and triggers stock alert if needed."""
        from app.worker.celery_worker import send_proactive_nudge
        
        score = await self.calculate_demand_score(sku_id)
        if score > threshold:
            logger.warning(f"THRESHOLD EXCEEDED: SKU {sku_id} has DemandScore {score}. Recommend Reorder.")
            # Trigger Nudge/Alert
            send_proactive_nudge.delay("test-customer-id", f"Urgent: Stock for SKU {sku_id} is running low based on demand signals.")
            return True
        return False
