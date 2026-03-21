from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


# AI and intent

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


class KhataActionEnum(str, Enum):
    PAYMENT_RECEIVED = "payment_received"
    CREDIT_GIVEN = "credit_given"


class KhataParsedRecord(BaseModel):
    customer_name: str
    amount: float
    action: KhataActionEnum
    confidence: float


# admin auth

class AdminLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# store and vendor

class StoreCreate(BaseModel):
    name: str
    contact_phone: str
    owner_name: str
    address: Optional[str] = None


class VendorCreate(BaseModel):
    name: str
    phone: str
    category: str


class AssignVendorRequest(BaseModel):
    store_id: str
    vendor_id: str


# inventory

class InventoryUpdateRequest(BaseModel):
    store_id: str
    sku_name: str
    quantity_delta: float = Field(..., description="Positive to add stock, negative to subtract")


# khata

class KhataAddRequest(BaseModel):
    customer_id: str = Field(..., description="UUID of the customer")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    action: Literal["payment_received", "credit_given"] = Field(
        ..., description="payment_received reduces balance; credit_given increases it"
    )


# notifications

class BroadcastRequest(BaseModel):
    message: str
    store_ids: Optional[list[str]] = Field(None, description="Specific stores; omit to target all")

