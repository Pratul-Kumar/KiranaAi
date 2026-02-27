from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class IntentEnum(str, Enum):
    STOCK_UPDATE = "stock_update"
    REORDER = "reorder"
    LOST_SALE = "lost_sale"
    KHATA_UPDATE = "khata_update"
    DELIVERY_CONFIRMATION = "delivery_confirmation"
    UNKNOWN = "unknown"

class AIIntentResponse(BaseModel):
    intent: IntentEnum = Field(..., description="The detected intent of the message")
    sku: Optional[str] = Field(None, description="The name of the item or SKU")
    quantity: Optional[float] = Field(1.0, description="The numeric quantity")
    customer_name: Optional[str] = Field(None, description="The customer name for Khata updates")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score of the extraction")
    original_text: Optional[str] = None
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the decision")

class TranscriptionResult(BaseModel):
    text: str
    confidence: float
    language: str = "hi"

class DemandScore(BaseModel):
    sku_id: str
    score: float
    breakdown: Dict[str, float]
    timestamp: str = Field(default_factory=lambda: "now")

class KhataActionEnum(str, Enum):
    PAYMENT_RECEIVED = "payment_received"
    CREDIT_GIVEN = "credit_given"

class KhataParsedRecord(BaseModel):
    customer_name: str
    amount: float
    action: KhataActionEnum
    confidence: float
