from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User
from app.schemas.customer import CustomerCreate, CustomerOut
from app.services.customer import create_customer_svc, get_customer_svc, list_customers_svc

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=dict)
def create_customer_endpoint(
    body: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    try:
        c = create_customer_svc(db, body)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": CustomerOut.model_validate(c), "message": "Customer created"}


@router.get("", response_model=dict)
def list_customers_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    rows, total = list_customers_svc(db, skip, limit, search)
    return {
        "success": True,
        "data": {
            "items": [CustomerOut.model_validate(c) for c in rows],
            "total": total,
        },
    }


@router.get("/{customer_id}", response_model=dict)
def get_customer_endpoint(
    customer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    c = get_customer_svc(db, customer_id)
    return {"success": True, "data": CustomerOut.model_validate(c)}


@router.get("/{customer_id}/bookings", response_model=dict)
def customer_bookings_endpoint(
    customer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    from app.db.models import Booking
    rows = (
        db.query(Booking)
        .filter(Booking.customer_id == customer_id)
        .order_by(Booking.event_date.desc())
        .all()
    )
    data = [
        {
            "id": str(b.id), "booking_code": b.booking_code, "event_type": b.event_type,
            "event_date": str(b.event_date), "slot": b.slot, "guest_count": b.guest_count,
            "total_price": str(b.total_price), "amount_paid": str(b.amount_paid),
            "balance_amount": str(b.balance_amount), "payment_status": b.payment_status,
            "status": b.status,
        } for b in rows
    ]
    return {"success": True, "data": data}


@router.get("/{customer_id}/summary", response_model=dict)
def customer_summary_endpoint(
    customer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    from app.db.models import Booking
    rows = db.query(Booking).filter(Booking.customer_id == customer_id).all()
    total_paid = sum(float(b.amount_paid) for b in rows if b.status != "cancelled")
    outstanding = sum(float(b.balance_amount) for b in rows if b.status != "cancelled" and b.balance_amount > 0)
    return {
        "success": True,
        "data": {
            "total_bookings": len(rows),
            "total_paid": total_paid,
            "total_outstanding": outstanding,
        },
    }
