import re

from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import date, time


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=20)
    role: str = Field(pattern="^(manager|reception|waiter|cook|cleaner|security|other)$")
    password: str | None = Field(default=None, min_length=8)
    cnic: str | None = Field(max_length=15, default=None)
    address: str | None = None
    hire_date: date | None = None
    duty_start_time: time | None = None
    monthly_salary: float | None = Field(default=None, ge=0)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_must_have_letter_and_number(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number")
        return value


class EmployeeOut(BaseModel):
    id: UUID
    employee_code: str
    full_name: str
    phone: str
    role: str
    cnic: str | None
    address: str | None
    hire_date: date | None
    duty_start_time: time | None
    monthly_salary: float | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
