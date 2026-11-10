from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Payment, Booking
from app.schemas.payment import PaymentCreate
from app.services.payment import record_payment, void_payment

router = APIRouter(tags=["payments"])


def _payment_dict(p: Payment) -> dict:
    return {
        "id": str(p.id), "booking_id": str(p.booking_id), "amount": float(p.amount),
        "payment_date": str(p.payment_date), "method": p.method, "reference": p.reference,
        "received_by": str(p.received_by), "receipt_number": p.receipt_number,
        "is_voided": p.is_voided, "void_reason": p.void_reason, "notes": p.notes,
        "created_at": str(p.created_at),
    }


@router.get("/payments/outstanding", response_model=dict)
def outstanding_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = db.query(Booking).filter(Booking.balance_amount > 0).order_by(Booking.event_date.asc()).all()
    return {"success": True, "data": [
        {
            "id": str(x.id), "booking_code": x.booking_code, "event_type": x.event_type,
            "event_date": str(x.event_date), "slot": x.slot, "total_price": float(x.total_price),
            "amount_paid": float(x.amount_paid), "balance_amount": float(x.balance_amount),
            "payment_status": x.payment_status, "status": x.status,
            "customer_name": x.customer.full_name if x.customer else None,
            "customer_phone": x.customer.phone if x.customer else None,
        } for x in rows
    ]}


@router.post("/bookings/{booking_id}/payments", response_model=dict)
def record_payment_endpoint(
    booking_id: UUID,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    try:
        payment = record_payment(db, booking_id, body, user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail={"code": "PAYMENT_EXCEEDS_BALANCE", "message": str(e)})
    return {"success": True, "data": _payment_dict(payment), "message": "Payment recorded"}


@router.get("/bookings/{booking_id}/payments", response_model=dict)
def list_payments_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = (
        db.query(Payment)
        .filter(Payment.booking_id == booking_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return {"success": True, "data": [_payment_dict(p) for p in rows]}


@router.get("/payments/{payment_id}/receipt", response_model=dict)
def receipt_endpoint(
    payment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Payment not found"})
    booking = db.get(Booking, payment.booking_id)
    return {
        "success": True,
        "data": {
            "receipt_number": payment.receipt_number,
            "booking_code": booking.booking_code if booking else None,
            "customer_id": str(booking.customer_id) if booking else None,
            "amount": float(payment.amount),
            "payment_date": str(payment.payment_date),
            "method": payment.method,
            "reference": payment.reference,
            "received_by": str(payment.received_by),
            "is_voided": payment.is_voided,
            "void_reason": payment.void_reason,
            "created_at": str(payment.created_at),
        },
    }


@router.post("/payments/{payment_id}/void", response_model=dict)
def void_payment_endpoint(
    payment_id: UUID,
    body: dict | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    reason = (body or {}).get("reason") or "Not specified"
    try:
        payment = void_payment(db, payment_id, user.id, str(reason))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": _payment_dict(payment), "message": "Payment voided"}
