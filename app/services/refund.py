from datetime import date as _date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import payment as payment_crud
from app.db.models import Booking, Refund


def next_credit_note_number(db: Session) -> str:
    year = _date.today().year
    row = db.execute(
        select(func.max(Refund.credit_note_no)).where(
            Refund.credit_note_no.like(f"CN-{year}-%")
        )
    ).scalar()
    n = 0
    if row:
        try:
            n = int(str(row).split("-")[-1])
        except Exception:
            n = 0
    return f"CN-{year}-{n + 1:04d}"


def record_refund(db: Session, booking_id: UUID, data, created_by: UUID) -> Refund:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})

    net_paid = float(booking.amount_paid)
    if data.amount > net_paid:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "REFUND_EXCEEDS_PAID",
                "message": f"Refund exceeds received amount of {net_paid}",
            },
        )

    refund = Refund(
        booking_id=booking_id,
        credit_note_no=next_credit_note_number(db),
        amount=data.amount,
        refund_date=data.refund_date,
        method=data.method,
        reference=data.reference,
        reason=data.reason,
        created_by=created_by,
    )
    db.add(refund)
    db.flush()
    payment_crud.recompute_booking_totals(db, booking)
    db.commit()
    db.refresh(refund)
    return refund
