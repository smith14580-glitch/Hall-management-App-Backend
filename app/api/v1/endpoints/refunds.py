from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Refund
from app.schemas.refund import RefundCreate
from app.services.refund import record_refund

router = APIRouter(tags=["refunds"])


def _refund_dict(r: Refund) -> dict:
    return {
        "id": str(r.id),
        "booking_id": str(r.booking_id),
        "credit_note_no": r.credit_note_no,
        "amount": float(r.amount),
        "refund_date": str(r.refund_date),
        "method": r.method,
        "reference": r.reference,
        "reason": r.reason,
        "created_by": str(r.created_by) if r.created_by else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.post("/bookings/{booking_id}/refunds", response_model=dict, status_code=201)
def create_refund_endpoint(
    booking_id: UUID,
    body: RefundCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    try:
        refund = record_refund(db, booking_id, body, user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": _refund_dict(refund), "message": "Refund recorded"}


@router.get("/bookings/{booking_id}/refunds", response_model=dict)
def list_booking_refunds_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = (
        db.query(Refund)
        .filter(Refund.booking_id == booking_id)
        .order_by(Refund.created_at.desc())
        .all()
    )
    return {"success": True, "data": [_refund_dict(r) for r in rows]}


@router.get("/refunds", response_model=dict)
def list_refunds_endpoint(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.query(Refund)
    if date_from:
        q = q.filter(Refund.refund_date >= date_from)
    if date_to:
        q = q.filter(Refund.refund_date <= date_to)
    rows = q.order_by(Refund.refund_date.desc(), Refund.created_at.desc()).all()
    return {
        "success": True,
        "data": [_refund_dict(r) for r in rows],
        "total": float(sum(float(r.amount) for r in rows)),
    }
