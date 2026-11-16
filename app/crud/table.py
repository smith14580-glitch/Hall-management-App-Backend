import uuid
from datetime import date
from typing import Optional

from sqlalchemy import func, select
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


def delete_table(db: Session, table_id: uuid.UUID) -> Optional[Table]:
    t = db.get(Table, table_id)
    if not t:
        return None
    used = db.execute(
        select(EventTableAllocation.id)
        .where(EventTableAllocation.table_id == table_id)
        .limit(1)
    ).scalar_one_or_none()
    if used:
        raise ValueError("Table has allocation history — deactivate it instead of deleting.")
    db.delete(t)
    db.commit()
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

def activate_table(db: Session, table_id: uuid.UUID) -> Optional[Table]:
    t = db.get(Table, table_id)
    if not t:
        return None
    t.is_active = True
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

    conflict_ids = db.execute(
        select(EventTableAllocation.table_id)
        .join(Booking, EventTableAllocation.booking_id == Booking.id)
        .where(
            EventTableAllocation.table_id.in_(table_ids),
            Booking.id != booking_id,
            Booking.event_date == booking.event_date,
            Booking.slot == booking.slot,
            Booking.status != "cancelled",
        )
    ).scalars().all()
    if conflict_ids:
        conflict_numbers = sorted(by_id[tid].table_number for tid in set(conflict_ids) if tid in by_id)
        raise ValueError(
            f"Tables already allocated in this date/slot: {', '.join(conflict_numbers)}"
        )

    # remove existing allocations then add new
    db.execute(
        EventTableAllocation.__table__.delete().where(EventTableAllocation.booking_id == booking_id)
    )
    for tid in table_ids:
        db.add(EventTableAllocation(booking_id=booking_id, table_id=tid, created_by=created_by))
    db.commit()
    return get_allocation_for_booking(db, booking_id)


def table_utilization(db: Session, hall_id: uuid.UUID, date_from: date, date_to: date):
    tables = db.execute(
        select(Table).where(Table.hall_id == hall_id).order_by(Table.table_number)
    ).scalars().all()
    counts = dict(
        db.execute(
            select(EventTableAllocation.table_id, func.count(func.distinct(Booking.id)))
            .join(Booking, EventTableAllocation.booking_id == Booking.id)
            .where(
                Booking.event_date >= date_from,
                Booking.event_date <= date_to,
                Booking.status != "cancelled",
            )
            .group_by(EventTableAllocation.table_id)
        ).all()
    )
    days = (date_to - date_from).days + 1
    total_slots = max(0, days * 2)
    return [
        {
            "table_id": str(t.id),
            "table_number": t.table_number,
            "capacity": t.capacity,
            "is_active": t.is_active,
            "booked_events": int(counts.get(t.id, 0)),
            "utilization_percent": round((counts.get(t.id, 0) / total_slots) * 100, 1) if total_slots else 0,
        }
        for t in tables
    ]


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
