from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import validation_error
from app.crud import payment as payment_crud
from app.db.models import Payment, Booking, User


def record_payment(db: Session, booking_id: UUID, data, received_by: UUID) -> Payment:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    if booking.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Cannot record payment on cancelled/completed booking"})

    remaining = booking.total_price - booking.amount_paid
    if data.amount > remaining:
        raise validation_error(
            f"Amount exceeds remaining balance of {remaining}. Remaining balance: {remaining}"
        )

    payment = payment_crud.create_payment_row(
        db,
        booking_id=booking_id,
        amount=data.amount,
        payment_date=data.payment_date,
        method=data.method,
        reference=data.reference,
        received_by=received_by,
        receipt_number=payment_crud.next_receipt_number(db),
        notes=data.notes,
    )
    payment_crud.recompute_booking_totals(db, booking)
    db.commit()
    db.refresh(payment)
    return payment


def void_payment(db: Session, payment_id: UUID, voided_by: UUID, reason: str) -> Payment:
    payment = payment_crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Payment not found"})
    if payment.is_voided:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Payment already voided"})
    booking = db.get(Booking, payment.booking_id)
    payment.is_voided = True
    payment.voided_by = voided_by
    payment.void_reason = reason
    db.add(payment)
    payment_crud.recompute_booking_totals(db, booking)
    db.commit()
    db.refresh(payment)
    return payment
