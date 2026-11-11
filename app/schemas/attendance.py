from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import date, datetime


class CheckInRequest(BaseModel):
    employee_id: UUID | None = None


class CheckOutRequest(BaseModel):
    employee_id: UUID | None = None

class ScanRequest(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40)
    action: str = Field(default="auto", pattern="^(auto|check-in|check-out)$")


class AttendanceOut(BaseModel):
    id: UUID
    employee_id: UUID
    attendance_date: date
    status: str
    check_in_at: datetime | None
    check_out_at: datetime | None
    is_late: bool
    late_minutes: int | None
    working_minutes: int | None
    check_in_method: str | None

    model_config = ConfigDict(from_attributes=True)
