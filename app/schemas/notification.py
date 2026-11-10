from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date


class NotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    body: str | None
    is_read: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ReportRequest(BaseModel):
    period: str = "monthly"  # daily|weekly|monthly|annual
    date_from: date | None = None
    date_to: date | None = None
    format: str = "json"  # json|csv|pdf
