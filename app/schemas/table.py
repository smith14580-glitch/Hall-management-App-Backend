from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class TableCreate(BaseModel):
    table_number: str = Field(min_length=1, max_length=20)
    capacity: int = Field(gt=0)


class TableOut(BaseModel):
    id: UUID
    hall_id: UUID
    table_number: str
    capacity: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TableAllocate(BaseModel):
    table_ids: list[UUID]
