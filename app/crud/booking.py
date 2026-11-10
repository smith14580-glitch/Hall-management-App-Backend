import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, joinedload

from app.db.models import Booking, Customer, Hall, User


def get_booking(db: Session, booking_id: uuid.UUID) -> Optional[Booking]:
    return db.get(Booking, booking_id)


def get_bookings(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    event_date: Optional[date] = None,
    slot: Optional[str] = None,
):
    q = select(Booking).options(joinedload(Booking.customer), joinedload(Booking.hall))
    if search:
        like = f"%{search}%"
        q = q.join(Customer, Customer.id == Booking.customer_id).where(
            (Booking.booking_code.ilike(like))
            | (Customer.full_name.ilike(like))
            | (Customer.phone.ilike(like))
        )
    if status:
        q = q.where(Booking.status == status)
    if event_date:
        q = q.where(Booking.event_date == event_date)
    if slot:
        q = q.where(Booking.slot == slot)
    q = q.order_by(Booking.event_date.desc(), Booking.created_at.desc())
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(q.offset(skip).limit(limit)).scalars().all()
    return rows, total


def create_booking_row(db: Session, **data) -> Booking:
    booking = Booking(**data)
    db.add(booking)
    db.flush()
    return booking


def update_booking_status(
    db: Session, booking: Booking, status: str, cancelled_by: Optional[uuid.UUID] = None,
    cancelled_reason: Optional[str] = None,
) -> Booking:
    booking.status = status
    if status == "cancelled":
        booking.cancelled_by = cancelled_by
        booking.cancelled_reason = cancelled_reason
    if status == "completed":
        from datetime import datetime, timezone
        booking.completed_at = datetime.now(timezone.utc)
    db.add(booking)
    db.flush()
    return booking
