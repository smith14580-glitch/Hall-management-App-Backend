from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

METHOD_PATTERN = "^(cash|bank_transfer|jazzcash|easypaisa|cheque|other)$"


class RefundCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    refund_date: date
    method: str = Field(pattern=METHOD_PATTERN)
    reason: str = Field(min_length=1)
    reference: str | None = Field(default=None, max_length=100)
