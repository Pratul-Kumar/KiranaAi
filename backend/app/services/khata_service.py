from app.db.supabase import get_supabase_admin_client
from app.services.ai.slm_service import SLMService
import logging
import json

logger = logging.getLogger(__name__)

class KhataService:
    """Handles khata digitization via OCR/Text parsing and LeadScore calculation."""
    
    def __init__(self):
        self.db = get_supabase_admin_client()
        self.slm = SLMService()

    async def parse_khata_record(self, text: str, store_id: str):
        """
        Parses a ledger update from text/voice.
        E.g., "Ramesh ne 500 rupaye diye" -> Update Ramesh's balance.
        """
        system_prompt = (
            "You are a Khata OCR/Text parser. Extract: customer_name, amount, "
            "action (payment_received, credit_given). Output ONLY JSON."
        )
        prompt = f"Ledger entry: \"{text}\"\nJSON Output:"
        
        parsed_str = await self.slm.generate_response(prompt, system_prompt)
        try:
            cleaned = parsed_str.strip("`").replace("json", "").strip()
            parsed = json.loads(cleaned)
        except:
            parsed = await self.slm.extract_intent_and_entities(text) # Fallback
        
        # 1. Resolve Customer
        customer_name = parsed.get("customer_name") or parsed.get("sku")
        cust_res = self.db.table("customers").select("id").ilike("name", f"%{customer_name}%").eq("store_id", store_id).execute()
        
        if not cust_res.data:
            return {"error": "Customer not found"}
            
        customer_id = cust_res.data[0]["id"]
        amount = float(parsed.get("amount") or parsed.get("quantity", 0))

        # 2. Update Ledger
        ledger_res = self.db.table("khata_ledger").select("balance").eq("customer_id", customer_id).execute()
        current_balance = ledger_res.data[0]["balance"] if ledger_res.data else 0
        
        # Logic: Payment received reduces balance, credit given increases it
        # This is a simplified implementation
        new_balance = float(current_balance) - amount
        
        self.db.table("khata_ledger").upsert({
            "customer_id": customer_id,
            "balance": new_balance,
            "last_payment_date": "now()",
            "updated_at": "now()"
        }).execute()
        
        # 3. Recalculate Lead Score
        await self.calculate_lead_score(customer_id)
        
        return {"status": "ledger_updated", "new_balance": new_balance}

    async def calculate_lead_score(self, customer_id: str):
        """
        LeadScore = Purchase Frequency + Avg Order Value + Payment Reliability
        """
        # Fetch transaction history for customer
        tx_res = self.db.table("transactions").select("total_amount, created_at").eq("customer_id", customer_id).execute()
        txs = tx_res.data
        
        if not txs:
            return 0.0

        frequency = len(txs) / 30.0 # tx per month (rough)
        avg_order_value = sum(t["total_amount"] for t in txs) / len(txs)
        reliability = 0.8 # Placeholder for payment lag calculation
        
        lead_score = (frequency * 0.4) + (avg_order_value * 1e-4 * 0.4) + (reliability * 0.2)
        lead_score = min(lead_score, 1.0) # Cap at 1.0
        
        self.db.table("khata_ledger").update({"lead_score": lead_score}).eq("customer_id", customer_id).execute()
        return lead_score
