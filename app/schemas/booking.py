import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class BookingCreate(BaseModel):
    customer_id: uuid.UUID
    hall_id: uuid.UUID
    event_type: str = Field(min_length=1, max_length=50)
    event_date: date
    slot: str = Field(pattern="^(day|night)$")
    guest_count: int = Field(gt=0)
    tables_required: int = Field(gt=0)
    special_instructions: str | None = None
    advance_amount: Decimal | None = None


class BookingOut(BaseModel):
    id: uuid.UUID
    booking_code: str
    customer_id: uuid.UUID
    hall_id: uuid.UUID
    event_type: str
    event_date: date
    slot: str
    guest_count: int
    tables_required: int
    special_instructions: str | None
    total_price: Decimal
    advance_amount: Decimal
    amount_paid: Decimal
    balance_amount: Decimal
    payment_status: str
    status: str
    created_by: uuid.UUID
    cancelled_by: uuid.UUID | None
    cancelled_reason: str | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
