from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Booking, Payment, Attendance

router = APIRouter(prefix="/reports", tags=["reports"])


def _csv(rows: list[dict], headers: list[str]) -> str:
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(h, "") for h in headers])
    return buf.getvalue()


@router.get("/bookings", response_model=dict)
def bookings_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    format: str = Query("json"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.query(Booking)
    if date_from:
        q = q.filter(Booking.event_date >= date_from)
    if date_to:
        q = q.filter(Booking.event_date <= date_to)
    rows = q.order_by(Booking.event_date.desc()).all()
    data = [
        {
            "booking_code": b.booking_code,
            "event_type": b.event_type,
            "event_date": str(b.event_date),
            "slot": b.slot,
            "guest_count": b.guest_count,
            "total_price": str(b.total_price),
            "amount_paid": str(b.amount_paid),
            "balance_amount": str(b.balance_amount),
            "payment_status": b.payment_status,
            "status": b.status,
        } for b in rows
    ]
    if format == "csv":
        return Response(content=_csv(data, ["booking_code","event_type","event_date","slot","guest_count","total_price","amount_paid","balance_amount","payment_status","status"]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=bookings_report.csv"})
    return {"success": True, "data": data}


@router.get("/revenue", response_model=dict)
def revenue_report(
    period: str = Query("monthly"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.query(Payment).filter(Payment.is_voided == False)  # noqa: E712
    if date_from:
        q = q.filter(Payment.payment_date >= date_from)
    if date_to:
        q = q.filter(Payment.payment_date <= date_to)
    rows = q.all()
    total = sum(float(p.amount) for p in rows)
    return {"success": True, "data": {"period": period, "total_revenue": total, "count": len(rows)}}


@router.get("/outstanding", response_model=dict)
def outstanding_report(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = db.query(Booking).filter(Booking.balance_amount > 0).order_by(Booking.event_date.asc()).all()
    data = [
        {
            "booking_code": b.booking_code,
            "event_date": str(b.event_date),
            "slot": b.slot,
            "total_price": str(b.total_price),
            "amount_paid": str(b.amount_paid),
            "balance_amount": str(b.balance_amount),
        } for b in rows
    ]
    return {"success": True, "data": data}
