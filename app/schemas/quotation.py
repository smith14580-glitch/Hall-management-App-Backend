from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class QuotationTemplateUpdate(BaseModel):
    template_body: Optional[str] = None
    facilities: Optional[str] = None
    chargeable_items: Optional[str] = None
    policies: Optional[str] = None
    office_timings: Optional[str] = None
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    location_link: Optional[str] = None
    validity_days: Optional[int] = Field(default=None, ge=1, le=365)


class QuotationTemplateOut(BaseModel):
    template_body: str
    facilities: Optional[str] = None
    chargeable_items: Optional[str] = None
    policies: Optional[str] = None
    office_timings: Optional[str] = None
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    location_link: Optional[str] = None
    validity_days: int = 7
    updated_at: Optional[datetime] = None


class QuotationCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=120)
    client_phone: str = Field(min_length=7, max_length=30)
    source: Optional[str] = Field(default=None, max_length=30)
    event_type: Optional[str] = Field(default=None, max_length=60)
    event_date: Optional[date] = None
    slot: Optional[str] = Field(default=None, pattern="^(day|night)$")
    guest_count: Optional[int] = Field(default=None, ge=0)
    hall_id: Optional[UUID] = None


class QuotationOut(BaseModel):
    id: str
    enquiry_no: str
    client_name: str
    client_phone: str
    source: Optional[str] = None
    event_type: Optional[str] = None
    event_date: Optional[date] = None
    slot: Optional[str] = None
    guest_count: Optional[int] = None
    hall_id: Optional[str] = None
    hall_name: Optional[str] = None
    package_price: Optional[float] = None
    advance_percent: Optional[int] = None
    message_body: Optional[str] = None
    status: str
    valid_until: Optional[date] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    whatsapp_url: Optional[str] = None
