from typing import Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Booking
from app.schemas.booking import BookingCreate
from app.schemas.table import TableAllocate
from app.services.booking import create_booking, list_bookings, get_booking, confirm_booking, cancel_booking, complete_booking
from app.services.table import get_allocations_svc, allocate_tables_svc, remove_allocation_svc

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _booking_dict(b: Booking) -> dict:
    cust = b.customer if b.customer is not None else None
    hall = b.hall if b.hall is not None else None
    return {
        "id": str(b.id), "booking_code": b.booking_code, "event_type": b.event_type,
        "event_date": str(b.event_date), "slot": b.slot, "guest_count": b.guest_count,
        "tables_required": b.tables_required, "special_instructions": b.special_instructions,
        "total_price": float(b.total_price), "advance_amount": float(b.advance_amount),
        "amount_paid": float(b.amount_paid), "balance_amount": float(b.balance_amount),
        "payment_status": b.payment_status, "status": b.status,
        "customer_id": str(b.customer_id), "customer_name": cust.full_name if cust else None,
        "customer_phone": cust.phone if cust else None,
        "hall_id": str(b.hall_id), "hall_name": hall.name if hall else None,
        "created_by": str(b.created_by),
    }


@router.post("", response_model=dict, status_code=201)
def create_booking_endpoint(
    body: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    try:
        booking = create_booking(db, body, user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=409, detail={"code": "BOOKING_CONFLICT", "message": str(e)})
    return {"success": True, "data": _booking_dict(booking), "message": "Booking created"}


@router.get("", response_model=dict)
def list_bookings_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    event_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    slot: Optional[str] = Query(None, pattern="^(day|night)$"),
    payment_status: Optional[str] = Query(None),
):
    rows, total = list_bookings(db, skip, limit, search, status, event_date, slot)
    return {
        "success": True,
        "data": {
            "items": [_booking_dict(x) for x in rows],
            "total": total,
            "page": skip // max(limit, 1) + 1,
            "page_size": limit,
        },
    }


@router.get("/upcoming", response_model=dict)
def upcoming_bookings_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = (
        db.query(Booking)
        .filter(Booking.status.in_(["pending", "confirmed"]), Booking.event_date >= date.today())
        .order_by(Booking.event_date.asc())
        .all()
    )
    return {"success": True, "data": [_booking_dict(b) for b in rows]}


@router.get("/today", response_model=dict)
def todays_bookings_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = db.query(Booking).filter(Booking.event_date == date.today()).order_by(Booking.slot.asc()).all()
    return {"success": True, "data": [_booking_dict(b) for b in rows]}


@router.get("/{booking_id}", response_model=dict)
def get_booking_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    b = get_booking(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    return {"success": True, "data": _booking_dict(b)}


@router.get("/{booking_id}/tables", response_model=dict)
def get_booking_tables_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = get_allocations_svc(db, booking_id)
    return {"success": True, "data": rows}


@router.post("/{booking_id}/tables", response_model=dict)
def allocate_booking_tables_endpoint(
    booking_id: UUID,
    body: TableAllocate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = allocate_tables_svc(db, booking_id, body.table_ids, user.id)
    return {"success": True, "data": rows, "message": "Tables allocated"}


@router.delete("/{booking_id}/tables/{table_id}", response_model=dict)
def remove_booking_table_endpoint(
    booking_id: UUID,
    table_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = remove_allocation_svc(db, booking_id, table_id, user.id)
    return {"success": True, "data": rows, "message": "Table removed"}


@router.post("/{booking_id}/confirm", response_model=dict)
def confirm_booking_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    b = get_booking(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    try:
        b = confirm_booking(db, b)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": _booking_dict(b), "message": "Booking confirmed"}


@router.post("/{booking_id}/cancel", response_model=dict)
def cancel_booking_endpoint(
    booking_id: UUID,
    body: dict = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    reason = (body or {}).get("reason") or "Not specified"
    b = get_booking(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    try:
        b = cancel_booking(db, b, user.id, str(reason))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": _booking_dict(b), "message": "Booking cancelled"}


@router.post("/{booking_id}/complete", response_model=dict)
def complete_booking_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    b = get_booking(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    try:
        b = complete_booking(db, b)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": _booking_dict(b), "message": "Booking completed"}
