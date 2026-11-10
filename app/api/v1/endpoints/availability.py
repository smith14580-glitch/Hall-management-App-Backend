from uuid import UUID
from datetime import date

from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import Booking

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("/check")
def check_availability(
    hall_id: UUID = Query(...),
    event_date: date = Query(...),
    slot: str = Query(..., pattern="^(day|night)$"),
    db: Session = Depends(get_db),
    _=Depends(require_role("super_admin")),
):
    conflict = db.execute(
        select(Booking.id).where(
            Booking.hall_id == hall_id,
            Booking.event_date == event_date,
            Booking.slot == slot,
            Booking.status.in_(["pending", "confirmed"]),
        )
    ).first()
    available = conflict is None
    return {
        "success": True,
        "data": {
            "available": available,
            "conflicting_booking_code": None,
        },
    }
