import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import Payment, Booking, Refund


def create_payment_row(db: Session, **data) -> Payment:
    payment = Payment(**data)
    db.add(payment)
    db.flush()
    return payment


def get_payment(db: Session, payment_id: uuid.UUID) -> Optional[Payment]:
    return db.get(Payment, payment_id)


def recompute_booking_totals(db: Session, booking: Booking) -> None:
    paid = (
        db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.booking_id == booking.id, Payment.is_voided == False  # noqa: E712
            )
        ).scalar()
        or Decimal("0")
    )
    refunded = (
        db.execute(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.booking_id == booking.id
            )
        ).scalar()
        or Decimal("0")
    )
    net_paid = max(Decimal("0"), paid - refunded)
    booking.amount_paid = net_paid
    booking.balance_amount = booking.total_price - net_paid
    if net_paid <= 0:
        booking.payment_status = "unpaid"
    elif net_paid < booking.total_price:
        booking.payment_status = "partially_paid"
    else:
        booking.payment_status = "fully_paid"
    db.add(booking)

def next_receipt_number(db: Session) -> str:
    from datetime import date as _date
    year = _date.today().year
    row = db.execute(
        select(func.max(Payment.receipt_number)).where(
            Payment.receipt_number.like(f"RCP-{year}-%")
        )
    ).scalar()
    n = 0
    if row:
        try:
            n = int(str(row).split("-")[-1])
        except Exception:
            n = 0
    return f"RCP-{year}-{n + 1:04d}"
