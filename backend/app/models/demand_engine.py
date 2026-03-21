from backend.app.db.supabase import get_supabase_admin_client
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import math

logger = logging.getLogger(__name__)


class DemandSensingEngine:
    """
    Production Demand Sensing Engine.
    DemandScore = (SalesVelocity * 0.4) + (DecayedLostSales * 0.4) + (Seasonality * 0.2)
    """

    def __init__(self) -> None:
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_supabase_admin_client()
        return self._db

    def _calculate_time_decay(self, timestamp_str: str, half_life_days: int = 7) -> float:
        """Applies exponential time decay to a signal."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = (now - dt).total_seconds() / 86400.0
            return math.exp(-0.693 * age_days / half_life_days)
        except (ValueError, TypeError):
            return 1.0

    def _sales_velocity(self, sku_id: str) -> float:
        """Counts transactions involving this SKU in the last 7 days, normalised to [0, 1]."""
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        res = (
            self.db.table("transactions")
            .select("id", count="exact")
            .eq("sku_id", sku_id)
            .gte("created_at", since)
            .execute()
        )
        count = res.count or 0
        return min(count / 20.0, 1.0)

    async def calculate_demand_score(self, sku_id: str) -> float:
        velocity = self._sales_velocity(sku_id)

        lost_sales_res = (
            self.db.table("lost_sales")
            .select("detected_at, requested_qty")
            .eq("sku_name", sku_id)
            .execute()
        )

        lost_score = 0.0
        for entry in lost_sales_res.data:
            decay = self._calculate_time_decay(entry["detected_at"])
            lost_score += float(entry["requested_qty"]) * decay
        lost_score_norm = min(lost_score / 10.0, 1.0)

        seasonality_impact = 0.2

        W_VELOCITY, W_LOST, W_SEASON = 0.4, 0.4, 0.2
        demand_score = round(
            min((velocity * W_VELOCITY) + (lost_score_norm * W_LOST) + (seasonality_impact * W_SEASON), 5.0),
            2,
        )

        self.db.table("demand_signals").insert({
            "sku_id": sku_id,
            "demand_score": demand_score,
            "velocity": velocity,
            "external_factors": {
                "lost_score_decayed": lost_score,
                "seasonality": seasonality_impact,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
            },
        }).execute()

        return demand_score

    async def check_threshold_and_alert(self, sku_id: str, threshold: float = 2.5) -> bool:
        score = await self.calculate_demand_score(sku_id)
        if score > threshold:
            logger.warning(f"HIGH_DEMAND | sku_id={sku_id} score={score}")
            return True
        return False
