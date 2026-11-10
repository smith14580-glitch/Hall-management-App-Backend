import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=20)
    email: str | None = None
    role_id: int
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    role_id: int
    full_name: str
    phone: str
    email: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
