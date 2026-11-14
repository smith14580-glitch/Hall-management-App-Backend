from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

CATEGORY_PATTERN = "^(catering|decoration|staff|utilities|maintenance|marketing|supplies|other)$"


class ExpenseCreate(BaseModel):
    category: str = Field(pattern=CATEGORY_PATTERN)
    vendor: str | None = Field(default=None, max_length=120)
    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    expense_date: date
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, pattern=CATEGORY_PATTERN)
    vendor: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, min_length=1)
    amount: Decimal | None = Field(default=None, gt=0)
    expense_date: date | None = None
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = None
