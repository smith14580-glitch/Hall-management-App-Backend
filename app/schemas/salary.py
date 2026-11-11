from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SalaryCreate(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    base_amount: Decimal = Field(ge=0)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    payment_date: date | None = None
    notes: str | None = None


class SalaryUpdate(BaseModel):
    base_amount: Decimal | None = Field(default=None, ge=0)
    paid_amount: Decimal | None = Field(default=None, ge=0)
    payment_date: date | None = None
    notes: str | None = None
    status: str | None = Field(default=None, pattern="^(pending|partial|paid)$")
