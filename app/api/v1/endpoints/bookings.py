from typing import Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.db.models import User, Booking
from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.table import TableAllocate
from app.services.booking import create_booking, list_bookings, get_booking, confirm_booking, cancel_booking, complete_booking
from app.services.table import get_allocations_svc, allocate_tables_svc, remove_allocation_svc

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
def create_booking_endpoint(
    body: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    try:
        return create_booking(db, body, user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=409, detail={"code": "BOOKING_CONFLICT", "message": str(e)})


@router.get("", response_model=dict)
def list_bookings_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    event_date: Optional[date] = Query(None),
    slot: Optional[str] = Query(None, pattern="^(day|night)$"),
):
    rows, total = list_bookings(db, skip, limit, search, status, event_date, slot)
    items = [
        {
            "id": str(x.id), "booking_code": x.booking_code, "event_type": x.event_type,
            "event_date": str(x.event_date), "slot": x.slot, "guest_count": x.guest_count,
            "tables_required": x.tables_required, "total_price": str(x.total_price),
            "advance_amount": str(x.advance_amount), "amount_paid": str(x.amount_paid),
            "balance_amount": str(x.balance_amount), "payment_status": x.payment_status,
            "status": x.status, "customer_id": str(x.customer_id), "hall_id": str(x.hall_id),
            "created_by": str(x.created_by),
        } for x in rows
    ]
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": skip // max(limit, 1) + 1,
            "page_size": limit,
        },
    }


@router.get("/{booking_id}", response_model=dict)
def get_booking_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    b = get_booking(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    return {"success": True, "data": {
        "id": str(b.id), "booking_code": b.booking_code, "event_type": b.event_type,
        "event_date": str(b.event_date), "slot": b.slot, "guest_count": b.guest_count,
        "tables_required": b.tables_required, "total_price": str(b.total_price),
        "advance_amount": str(b.advance_amount), "amount_paid": str(b.amount_paid),
        "balance_amount": str(b.balance_amount), "payment_status": b.payment_status,
        "status": b.status, "customer_id": str(b.customer_id), "hall_id": str(b.hall_id),
        "created_by": str(b.created_by),
    }}


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
    return {"success": True, "data": {"id": str(b.id), "status": b.status}, "message": "Booking confirmed"}


@router.post("/{booking_id}/cancel", response_model=dict)
def cancel_booking_endpoint(
    booking_id: UUID,
    reason: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    b = get_booking(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Booking not found"})
    try:
        b = cancel_booking(db, b, user.id, reason)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": {"id": str(b.id), "status": b.status, "reason": b.cancelled_reason}, "message": "Booking cancelled"}


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
    return {"success": True, "data": {"id": str(b.id), "status": b.status}, "message": "Booking completed"}
