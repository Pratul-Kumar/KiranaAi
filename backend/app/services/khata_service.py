from app.db.supabase import get_supabase_admin_client
from app.services.ai.slm_service import SLMService
from app.schemas.ai_schemas import AIIntentResponse, KhataParsedRecord, KhataActionEnum
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class KhataService:
    """Handles production-grade khata digitization and LeadScore calculation."""
    
    def __init__(self):
        self.db = get_supabase_admin_client()
        self.slm = SLMService()

    async def parse_khata_record(self, text: str, store_id: str):
        """
        Parses a ledger update from text/voice with structured validation.
        """
        system_prompt = (
            "You are a Khata OCR/Text parser. Extract the following into JSON:\n"
            "- customer_name: string\n"
            "- amount: float\n"
            "- action: \"payment_received\" | \"credit_given\"\n"
            "- confidence: 0.0-1.0\n"
            "Output ONLY valid JSON."
        )
        prompt = f"Ledger entry: \"{text}\"\nJSON Output:"
        
        try:
            raw_response = await self.slm._call_llm(prompt, system_prompt)
            data = json.loads(raw_response.strip("`").replace("json", "").strip())
            parsed = KhataParsedRecord(**data)
        except Exception as e:
            logger.error(f"Khata Parsing Failed: {e}")
            # Fallback or error
            return {"error": "Failed to parse ledger entry"}
        
        # 1. Resolve Customer
        cust_res = self.db.table("customers").select("id").ilike("name", f"%{parsed.customer_name}%").eq("store_id", store_id).execute()
        
        if not cust_res.data:
            # Proactive: Create customer if not exists? For MVP, just return error
            return {"error": f"Customer '{parsed.customer_name}' not found"}
            
        customer_id = cust_res.data[0]["id"]

        # 2. Update Ledger
        ledger_res = self.db.table("khata_ledger").select("balance").eq("customer_id", customer_id).execute()
        current_balance = float(ledger_res.data[0]["balance"]) if ledger_res.data else 0.0
        
        # Logic: Payment received reduces balance, credit given increases it
        if parsed.action == KhataActionEnum.PAYMENT_RECEIVED:
            new_balance = current_balance - parsed.amount
        else:
            new_balance = current_balance + parsed.amount
        
        self.db.table("khata_ledger").upsert({
            "customer_id": customer_id,
            "balance": new_balance,
            "last_payment_date": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        # 3. Recalculate Lead Score (Async)
        await self.calculate_lead_score(customer_id)
        
        return {
            "status": "ledger_updated",
            "customer": parsed.customer_name,
            "action": parsed.action,
            "amount": parsed.amount,
            "new_balance": new_balance
        }

    async def calculate_lead_score(self, customer_id: str):
        """
        Enhanced LeadScore with normalized features and risk prediction.
        """
        # Fetch transaction history & ledger
        tx_res = self.db.table("transactions").select("total_amount, created_at").eq("customer_id", customer_id).execute()
        ledger_res = self.db.table("khata_ledger").select("balance, last_payment_date").eq("customer_id", customer_id).execute()
        
        txs = tx_res.data
        if not txs:
            return 0.0

        # Frequency: Transactions in last 30 days
        frequency = len(txs) / 30.0 
        
        # Average Order Value (Normalized)
        avg_ov = sum(t["total_amount"] for t in txs) / len(txs)
        norm_aov = min(avg_ov / 5000.0, 1.0) # Assume 5000 is a high AOV
        
        # Payment Reliability (Based on balance vs AOV and last payment)
        balance = float(ledger_res.data[0]["balance"]) if ledger_res.data else 0.0
        reliability = 1.0 - min(balance / (avg_ov * 5 + 1), 1.0) # Risk increases if balance > 5x AOV
        
        lead_score = (frequency * 0.3) + (norm_aov * 0.4) + (reliability * 0.3)
        lead_score = round(min(max(lead_score, 0.0), 1.0), 2)
        
        self.db.table("khata_ledger").update({"lead_score": lead_score}).eq("customer_id", customer_id).execute()
        
        logger.info(f"Lead Score UPDATED for {customer_id}: {lead_score} (Freq: {frequency:.2f}, AOV: {norm_aov:.2f}, Rel: {reliability:.2f})")
        return lead_score
