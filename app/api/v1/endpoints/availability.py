from uuid import UUID
from datetime import date
import calendar

from sqlalchemy import select
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import Booking, Hall

router = APIRouter(prefix="/availability", tags=["availability"])


def _status_of(rows: list[Booking]) -> str:
    for b in rows:
        if b.status == "confirmed":
            return "booked"
    for b in rows:
        if b.status == "pending":
            return "pending"
    return "available"


@router.get("")
def month_availability(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    hall_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role("super_admin")),
):
    if hall_id:
        hall = db.get(Hall, hall_id)
    else:
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
    if not hall:
        return {"success": True, "data": []}

    year, mon = int(month[:4]), int(month[5:7])
    first = date(year, mon, 1)
    last = date(year, mon, calendar.monthrange(year, mon)[1])
    rows = (
        db.query(Booking)
        .filter(Booking.hall_id == hall.id, Booking.event_date >= first, Booking.event_date <= last)
        .all()
    )
    by_date: dict = {}
    for b in rows:
        by_date.setdefault(b.event_date, []).append(b)

    days = []
    d = first
    while d <= last:
        rows_for_day = by_date.get(d, [])
        day_active = [b for b in rows_for_day if b.slot == "day"]
        night_active = [b for b in rows_for_day if b.slot == "night"]
        days.append({
            "date": str(d),
            "day": {"status": _status_of(day_active)},
            "night": {"status": _status_of(night_active)},
        })
        d = date.fromordinal(d.toordinal() + 1)
    return {"success": True, "data": days}


@router.get("/check")
def check_availability(
    hall_id: UUID | None = Query(None),
    event_date: date = Query(...),
    slot: str = Query(..., pattern="^(day|night)$"),
    db: Session = Depends(get_db),
    _=Depends(require_role("super_admin")),
):
    if hall_id:
        hall = db.get(Hall, hall_id)
    else:
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
    if not hall:
        return {"success": True, "data": {"available": False, "conflicting_booking_code": None}}
    clash = (
        db.query(Booking)
        .filter(
            Booking.hall_id == hall.id,
            Booking.event_date == event_date,
            Booking.slot == slot,
            Booking.status.in_(["pending", "confirmed"]),
        )
        .first()
    )
    return {
        "success": True,
        "data": {
            "available": clash is None,
            "conflicting_booking_code": clash.booking_code if clash else None,
        },
    }
