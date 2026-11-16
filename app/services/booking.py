import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import conflict
from app.crud import booking as booking_crud
from app.crud import payment as payment_crud
from app.crud.notification import create_notification
from app.db.models import Booking, Customer, Hall, ApplicationSetting


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.execute(select(ApplicationSetting).where(ApplicationSetting.key == key)).scalar_one_or_none()
    return row.value if row else default


def _decimal_setting(db: Session, key: str, default: str) -> Decimal:
    raw = _get_setting(db, key, default)
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return Decimal(str(default))


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
    fallback = hall.day_price if slot == "day" else hall.night_price
    key = "hall_day_price" if slot == "day" else "hall_night_price"
    return _decimal_setting(db, key, str(fallback))


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
        # Keep the customer record in sync with the name/address the manager typed.
        typed_name = (data.customer_name or "").strip()
        if typed_name and typed_name != cust.full_name:
            cust.full_name = typed_name
        typed_address = (data.address or "").strip()
        if typed_address and typed_address != (cust.address or ""):
            cust.address = typed_address
        db.add(cust)
        db.flush()
        return cust.id
    cust = Customer(full_name=data.customer_name or data.phone, phone=data.phone, address=(data.address or "").strip() or None)
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
    customer = db.get(Customer, customer_id)
    customer_name_snapshot = data.customer_name.strip() if data.customer_name else (customer.full_name if customer else None)
    customer_phone_snapshot = data.phone or (customer.phone if customer else None)

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

    # Snapshot hall price (settings value, falling back to the hall record)
    hall_price = _hall_price(db, hall.id, data.slot)

    # Guest pricing (per guest)
    guest_rate = _decimal_setting(db, "guest_price_per_guest", "0")
    guest_amount = Decimal(str(data.guest_count)) * guest_rate

    # Refreshment (per guest, option-based; custom rate comes from the request)
    refreshment_type = data.refreshment_type or "none"
    refreshment_custom_name = None
    refreshment_guests = 0
    refreshment_rate = Decimal("0")
    if refreshment_type != "none":
        refreshment_guests = int(data.refreshment_guests or 0)
        rate_key = {
            "water": "addon_refreshment_water_per_guest",
            "juice": "addon_refreshment_juice_per_guest",
            "both": "addon_refreshment_both_per_guest",
        }.get(refreshment_type)
        if rate_key:
            refreshment_rate = _decimal_setting(db, rate_key, "0")
        elif refreshment_type == "custom":
            refreshment_rate = data.refreshment_rate if data.refreshment_rate is not None else Decimal("0")
            if refreshment_rate < 0:
                refreshment_rate = Decimal("0")
            refreshment_custom_name = data.refreshment_custom_name
    refreshment_amount = Decimal(refreshment_guests) * refreshment_rate

    # Hall type (flat per event)
    hall_type = data.hall_type or "ac"
    hall_type_rate = _decimal_setting(
        db,
        "addon_ac_price" if hall_type == "ac" else "addon_non_ac_price",
        "20000" if hall_type == "ac" else "0",
    )
    hall_type_amount = hall_type_rate

    total_price = hall_price + guest_amount + refreshment_amount + hall_type_amount

    # Advance default
    advance_percent = _decimal_setting(db, "default_advance_percent", "50")
    advance_amount = data.advance_amount if data.advance_amount is not None else (total_price * advance_percent / 100)
    if advance_amount < 0:
        advance_amount = Decimal("0")
    if advance_amount > total_price:
        advance_amount = total_price

    booking_code = _next_booking_code(db, data.event_date)

    booking = booking_crud.create_booking_row(
        db,
        booking_code=booking_code,
        customer_id=customer_id,
        customer_name=customer_name_snapshot,
        customer_phone=customer_phone_snapshot,
        hall_id=hall.id,
        event_type=data.event_type,
        event_date=data.event_date,
        slot=data.slot,
        guest_count=data.guest_count,
        tables_required=data.tables_required,
        special_instructions=data.special_instructions,
        refreshment_type=refreshment_type,
        refreshment_custom_name=refreshment_custom_name,
        refreshment_guests=refreshment_guests,
        refreshment_rate=refreshment_rate,
        refreshment_amount=refreshment_amount,
        hall_type=hall_type,
        hall_type_rate=hall_type_rate,
        hall_type_amount=hall_type_amount,
        guest_rate=guest_rate,
        guest_amount=guest_amount,
        total_price=total_price,
        advance_amount=advance_amount,
        amount_paid=Decimal("0"),
        balance_amount=total_price,
        payment_status="unpaid",
        status="pending",
        created_by=created_by,
    )
    db.flush()
    if advance_amount and advance_amount > 0:
        payment_crud.create_payment_row(
            db,
            booking_id=booking.id,
            amount=advance_amount,
            payment_date=date.today(),
            method="advance",
            reference=None,
            received_by=created_by,
            receipt_number=payment_crud.next_receipt_number(db),
            notes="Advance received at booking creation",
        )
        payment_crud.recompute_booking_totals(db, booking)
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
    booking.confirmed_at = datetime.now(timezone.utc)
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
