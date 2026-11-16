import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class BookingCreate(BaseModel):
    # Either an existing customer_id, OR customer details to auto-create/link (§6.2)
    customer_id: uuid.UUID | None = None
    customer_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    hall_id: uuid.UUID | None = None  # optional: defaults to the single hall
    event_type: str = Field(min_length=1, max_length=50)
    event_date: date
    slot: str = Field(pattern="^(day|night)$")
    guest_count: int = Field(gt=0)
    tables_required: int = Field(gt=0)
    special_instructions: str | None = None
    advance_amount: Decimal | None = None
    refreshment_type: Literal["none", "water", "juice", "both", "custom"] = "none"
    refreshment_custom_name: str | None = Field(default=None, max_length=100)
    refreshment_guests: int | None = Field(default=None, ge=0)
    refreshment_rate: Decimal | None = Field(default=None, ge=0)
    refreshment_amount: Decimal | None = Field(default=None, ge=0)
    hall_type: Literal["ac", "non_ac"] = "ac"
    hall_type_rate: Decimal | None = Field(default=None, ge=0)
    hall_type_amount: Decimal | None = Field(default=None, ge=0)
    guest_rate: Decimal | None = Field(default=None, ge=0)
    guest_amount: Decimal | None = Field(default=None, ge=0)


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
    refreshment_type: str
    refreshment_custom_name: str | None
    refreshment_guests: int | None
    refreshment_rate: Decimal | None
    refreshment_amount: Decimal
    hall_type: str
    hall_type_rate: Decimal | None
    hall_type_amount: Decimal
    guest_rate: Decimal
    guest_amount: Decimal
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
