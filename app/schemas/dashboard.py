from pydantic import BaseModel, ConfigDict
from typing import Optional


class SettingUpdate(BaseModel):
    value: str


class SettingOut(BaseModel):
    key: str
    value: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    total_revenue: float
    total_outstanding: float
    today_events: int
    total_customers: int
    total_employees: int
    present_today: int

    model_config = ConfigDict(from_attributes=True)
