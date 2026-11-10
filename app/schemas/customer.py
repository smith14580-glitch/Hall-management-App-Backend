from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=20)
    alternate_phone: str | None = Field(max_length=20, default=None)
    address: str | None = None
    email: str | None = None
    notes: str | None = None


class CustomerOut(BaseModel):
    id: UUID
    full_name: str
    phone: str
    alternate_phone: str | None
    address: str | None
    email: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
