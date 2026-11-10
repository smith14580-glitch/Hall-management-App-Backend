import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import conflict
from app.crud import booking as booking_crud
from app.crud.notification import create_notification
from app.db.models import Booking, Customer, Hall, ApplicationSetting


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.execute(select(ApplicationSetting).where(ApplicationSetting.key == key)).scalar_one_or_none()
    return row.value if row else default


def _next_booking_code(db: Session, event_date: date) -> str:
    year = event_date.year
    count = db.execute(
        select(func.count(Booking.id)).where(
            Booking.booking_code.like(f"MQ-{year}-%")
        )
    ).scalar() or 0
    return f"MQ-{year}-{count + 1:04d}"


def _hall_price(db: Session, hall_id: uuid.UUID, slot: str) -> Decimal:
    hall = db.get(Hall, hall_id)
    if not hall:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Hall not found"})
    return Decimal(str(hall.day_price if slot == "day" else hall.night_price))


def _resolve_customer(db: Session, data) -> uuid.UUID:
    """customer_id given → use it. Else phone given → link existing or create (§6.2)."""
    if data.customer_id:
        cust = db.get(Customer, data.customer_id)
        if not cust:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Customer not found"})
        return cust.id
    if not data.phone or not (data.customer_name or data.phone):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "customer_id or customer_name + phone required"})
    cust = db.execute(select(Customer).where(Customer.phone == data.phone)).scalar_one_or_none()
    if cust:
        return cust.id
    cust = Customer(full_name=data.customer_name or data.phone, phone=data.phone)
    db.add(cust)
    db.flush()
    return cust.id


def create_booking(db: Session, data, created_by: uuid.UUID) -> Booking:
    # Hall: explicit id, else the single seeded hall
    if data.hall_id:
        hall = db.get(Hall, data.hall_id)
    else:
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
    if not hall:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Hall not found"})

    customer_id = _resolve_customer(db, data)

    # Conflict safeguard: lock any active booking for same hall/date/slot
    existing = db.execute(
        select(Booking.id)
        .where(
            Booking.hall_id == hall.id,
            Booking.event_date == data.event_date,
            Booking.slot == data.slot,
            Booking.status.in_(["pending", "confirmed"]),
        )
        .with_for_update()
    ).first()
    if existing:
        raise conflict("BOOKING_CONFLICT", "This date and slot are already booked.")

    # Snapshot price
    total_price = Decimal(str(hall.day_price if data.slot == "day" else hall.night_price))

    # Advance default
    advance_percent = Decimal(_get_setting(db, "default_advance_percent", "50"))
    advance_amount = data.advance_amount if data.advance_amount is not None else (total_price * advance_percent / 100)

    booking_code = _next_booking_code(db, data.event_date)

    booking = booking_crud.create_booking_row(
        db,
        booking_code=booking_code,
        customer_id=customer_id,
        hall_id=hall.id,
        event_type=data.event_type,
        event_date=data.event_date,
        slot=data.slot,
        guest_count=data.guest_count,
        tables_required=data.tables_required,
        special_instructions=data.special_instructions,
        total_price=total_price,
        advance_amount=advance_amount,
        amount_paid=Decimal("0"),
        balance_amount=total_price,
        payment_status="unpaid",
        status="pending",
        created_by=created_by,
    )
    db.commit()
    db.refresh(booking)
    create_notification(
        db, created_by, "booking_created", f"Booking {booking_code} created",
        f"{data.event_type} on {data.event_date} ({data.slot})",
        related_booking_id=booking.id,
    )
    return booking


def list_bookings(db, skip=0, limit=100, search=None, status=None, event_date=None, slot=None):
    return booking_crud.get_bookings(db, skip, limit, search, status, event_date, slot)


def get_booking(db: Session, booking_id: uuid.UUID):
    return booking_crud.get_booking(db, booking_id)


def confirm_booking(db: Session, booking: Booking) -> Booking:
    if booking.status != "pending":
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Only pending bookings can be confirmed"})
    booking.status = "confirmed"
    db.add(booking)
    db.commit()
    db.refresh(booking)
    create_notification(
        db, booking.created_by, "booking_confirmed", f"Booking {booking.booking_code} confirmed",
        f"{booking.event_type} on {booking.event_date} ({booking.slot})",
        related_booking_id=booking.id,
    )
    return booking


def cancel_booking(db: Session, booking: Booking, cancelled_by: uuid.UUID, reason: str) -> Booking:
    if booking.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Cannot cancel a cancelled/completed booking"})
    booking.status = "cancelled"
    booking.cancelled_by = cancelled_by
    booking.cancelled_reason = reason
    db.add(booking)
    db.commit()
    db.refresh(booking)
    create_notification(
        db, cancelled_by, "booking_cancelled", f"Booking {booking.booking_code} cancelled",
        f"Reason: {reason}",
        related_booking_id=booking.id,
    )
    return booking


def complete_booking(db: Session, booking: Booking) -> Booking:
    if booking.status != "confirmed":
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Only confirmed bookings can be completed"})
    booking.status = "completed"
    booking.completed_at = datetime.now(timezone.utc)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    create_notification(
        db, booking.created_by, "booking_completed", f"Booking {booking.booking_code} completed",
        f"{booking.event_type} on {booking.event_date} ({booking.slot})",
        related_booking_id=booking.id,
    )
    return booking
