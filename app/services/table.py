from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import table as table_crud
from app.db.models import Table, EventTableAllocation, Booking


def list_tables_svc(db: Session, hall_id: UUID):
    return table_crud.list_tables(db, hall_id)


def create_table_svc(db: Session, hall_id: UUID, table_number: str, capacity: int) -> Table:
    return table_crud.create_table(db, hall_id, table_number, capacity)


def deactivate_table_svc(db: Session, table_id: UUID):
    t = table_crud.deactivate_table(db, table_id)
    if not t:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Table not found"})
    return t


def get_allocations_svc(db: Session, booking_id: UUID):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    rows = table_crud.get_allocation_for_booking(db, booking_id)
    return [
        {
            "id": str(r.id), "table_id": str(r.table_id), "table_number": r.table.table_number,
            "capacity": r.table.capacity,
        } for r in rows
    ]


def allocate_tables_svc(db: Session, booking_id: UUID, table_ids: list[UUID], created_by: UUID):
    try:
        rows = table_crud.allocate_tables(db, booking_id, table_ids, created_by)
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return [
        {
            "id": str(r.id), "table_id": str(r.table_id), "table_number": r.table.table_number,
            "capacity": r.table.capacity,
        } for r in rows
    ]


def remove_allocation_svc(db: Session, booking_id: UUID, table_id: UUID, created_by: UUID):
    try:
        rows = table_crud.remove_allocation(db, booking_id, table_id, created_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return [
        {
            "id": str(r.id), "table_id": str(r.table_id), "table_number": r.table.table_number,
            "capacity": r.table.capacity,
        } for r in rows
    ]
