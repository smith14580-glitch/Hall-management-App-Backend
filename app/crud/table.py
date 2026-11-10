import uuid
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, joinedload

from app.db.models import Table, EventTableAllocation, Booking, Hall


def list_tables(db: Session, hall_id: uuid.UUID):
    q = select(Table).where(Table.hall_id == hall_id).order_by(Table.table_number)
    return db.execute(q).scalars().all()


def create_table(db: Session, hall_id: uuid.UUID, table_number: str, capacity: int) -> Table:
    t = Table(hall_id=hall_id, table_number=table_number, capacity=capacity, is_active=True)
    db.add(t)
    db.flush()
    db.commit()
    db.refresh(t)
    return t


def deactivate_table(db: Session, table_id: uuid.UUID) -> Optional[Table]:
    t = db.get(Table, table_id)
    if not t:
        return None
    t.is_active = False
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def get_allocation_for_booking(db: Session, booking_id: uuid.UUID):
    q = (
        select(EventTableAllocation)
        .options(joinedload(EventTableAllocation.table))
        .where(EventTableAllocation.booking_id == booking_id)
    )
    return db.execute(q).scalars().all()


def allocate_tables(db: Session, booking_id: uuid.UUID, table_ids: list[uuid.UUID], created_by: uuid.UUID):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise ValueError("Booking not found")
    hall = db.get(Hall, booking.hall_id)
    if not hall:
        raise ValueError("Hall not found")

    # lock tables
    rows = db.execute(
        select(Table).where(Table.id.in_(table_ids)).with_for_update()
    ).scalars().all()
    by_id = {t.id: t for t in rows}
    if len(by_id) != len(table_ids):
        raise ValueError("One or more tables not found")

    active_count = sum(1 for t in rows if t.is_active)
    if active_count != len(table_ids):
        raise ValueError("Some tables are inactive")

    total_capacity = sum(t.capacity for t in rows)
    if total_capacity < booking.guest_count:
        raise ValueError(f"Allocated tables seat {total_capacity}, but guests are {booking.guest_count}")
    if len(table_ids) > hall.capacity_tables:
        raise ValueError(f"Cannot allocate {len(table_ids)} tables; hall capacity is {hall.capacity_tables}")

    # remove existing allocations then add new
    db.execute(
        EventTableAllocation.__table__.delete().where(EventTableAllocation.booking_id == booking_id)
    )
    for tid in table_ids:
        db.add(EventTableAllocation(booking_id=booking_id, table_id=tid, created_by=created_by))
    db.commit()
    return get_allocation_for_booking(db, booking_id)


def remove_allocation(db: Session, booking_id: uuid.UUID, table_id: uuid.UUID, created_by: uuid.UUID):
    row = db.execute(
        select(EventTableAllocation).where(
            EventTableAllocation.booking_id == booking_id,
            EventTableAllocation.table_id == table_id,
        )
    ).scalar_one_or_none()
    if not row:
        raise ValueError("Allocation not found")
    db.delete(row)
    db.commit()
    return get_allocation_for_booking(db, booking_id)
