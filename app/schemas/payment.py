from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import date
from uuid import UUID


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_date: date
    method: str = Field(pattern="^(cash|bank_transfer|jazzcash|easypaisa|cheque|other)$")
    reference: str | None = None
    notes: str | None = None


class PaymentOut(BaseModel):
    id: UUID
    booking_id: UUID
    amount: Decimal
    payment_date: date
    method: str
    reference: str | None
    received_by: UUID
    receipt_number: str
    is_voided: bool
    void_reason: str | None
    notes: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)
