from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Booking, Payment, Attendance, Expense, Refund

router = APIRouter(prefix="/reports", tags=["reports"])
router_audit = APIRouter(prefix="/audit-logs", tags=["audit"])


def _csv(rows: list[dict], headers: list[str]) -> str:
    import csv
    import io
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
    return {"success": True, "data": [{"period": period, "total_revenue": total, "payments_count": len(rows)}]}


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


@router.get("/profit-loss", response_model=dict)
def profit_loss_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    pay_q = db.query(Payment).filter(Payment.is_voided == False)  # noqa: E712
    ref_q = db.query(Refund)
    exp_q = db.query(Expense)
    if date_from:
        pay_q = pay_q.filter(Payment.payment_date >= date_from)
        ref_q = ref_q.filter(Refund.refund_date >= date_from)
        exp_q = exp_q.filter(Expense.expense_date >= date_from)
    if date_to:
        pay_q = pay_q.filter(Payment.payment_date <= date_to)
        ref_q = ref_q.filter(Refund.refund_date <= date_to)
        exp_q = exp_q.filter(Expense.expense_date <= date_to)

    payments = pay_q.all()
    refunds = ref_q.all()
    expenses = exp_q.all()

    gross_received = sum(float(p.amount) for p in payments)
    refunded = sum(float(r.amount) for r in refunds)
    expense_total = sum(float(e.amount) for e in expenses)
    net_revenue = gross_received - refunded

    by_category: dict[str, float] = {}
    for e in expenses:
        by_category[e.category] = by_category.get(e.category, 0.0) + float(e.amount)

    by_method: dict[str, float] = {}
    for p in payments:
        by_method[p.method] = by_method.get(p.method, 0.0) + float(p.amount)

    return {
        "success": True,
        "data": {
            "gross_received": gross_received,
            "refunded": refunded,
            "net_revenue": net_revenue,
            "expenses": expense_total,
            "profit": net_revenue - expense_total,
            "by_category": by_category,
            "by_method": by_method,
            "payments_count": len(payments),
            "refunds_count": len(refunds),
            "expenses_count": len(expenses),
        },
    }


@router.get("/cash-closing", response_model=dict)
def cash_closing_report(
    closing_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    target = closing_date or date.today()
    payments = (
        db.query(Payment)
        .filter(Payment.payment_date == target, Payment.is_voided == False)  # noqa: E712
        .all()
    )
    refunds = db.query(Refund).filter(Refund.refund_date == target).all()

    received_by_method: dict[str, float] = {}
    refunded_by_method: dict[str, float] = {}
    transactions = []
    for p in payments:
        received_by_method[p.method] = received_by_method.get(p.method, 0.0) + float(p.amount)
        transactions.append({
            "type": "payment",
            "method": p.method,
            "amount": float(p.amount),
            "reference": p.reference,
            "receipt_number": p.receipt_number,
            "booking_id": str(p.booking_id),
        })
    for r in refunds:
        refunded_by_method[r.method] = refunded_by_method.get(r.method, 0.0) + float(r.amount)
        transactions.append({
            "type": "refund",
            "method": r.method,
            "amount": -float(r.amount),
            "reference": r.reference,
            "receipt_number": r.credit_note_no,
            "booking_id": str(r.booking_id),
        })

    methods = sorted(set(received_by_method) | set(refunded_by_method))
    net_by_method = {
        m: received_by_method.get(m, 0.0) - refunded_by_method.get(m, 0.0) for m in methods
    }
    return {
        "success": True,
        "data": {
            "date": str(target),
            "received_by_method": received_by_method,
            "refunded_by_method": refunded_by_method,
            "net_by_method": net_by_method,
            "total_received": sum(received_by_method.values()),
            "total_refunded": sum(refunded_by_method.values()),
            "net_total": sum(net_by_method.values()),
            "transactions": transactions,
        },
    }


@router.get("/occupancy", response_model=dict)
def occupancy_report(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    import calendar as _cal

    if month:
        y, m = int(month[:4]), int(month[5:7])
    else:
        today = date.today()
        y, m = today.year, today.month
    first = date(y, m, 1)
    last = date(y, m, _cal.monthrange(y, m)[1])
    rows = (
        db.query(Booking)
        .filter(Booking.event_date >= first, Booking.event_date <= last, Booking.status != "cancelled")
        .all()
    )
    total_slots = _cal.monthrange(y, m)[1] * 2
    booked_slots = len(rows)
    by_slot = {
        "day": sum(1 for b in rows if b.slot == "day"),
        "night": sum(1 for b in rows if b.slot == "night"),
    }
    return {
        "success": True,
        "data": {
            "month": f"{y:04d}-{m:02d}",
            "total_slots": total_slots,
            "booked_slots": booked_slots,
            "free_slots": max(0, total_slots - booked_slots),
            "occupancy_percent": round((booked_slots / total_slots) * 100, 1) if total_slots else 0,
            "by_slot": by_slot,
        },
    }


@router.get("/attendance", response_model=dict)
def attendance_report(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    format: str = Query("json"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    from app.db.models import Employee
    from datetime import date as _date
    q = db.query(Attendance)
    if month:
        import calendar as _cal
        y, m = int(month[:4]), int(month[5:7])
        first = _date(y, m, 1)
        last = _date(y, m, _cal.monthrange(y, m)[1])
        q = q.filter(Attendance.attendance_date >= first, Attendance.attendance_date <= last)
    rows = q.order_by(Attendance.attendance_date.desc()).all()
    employees = {e.id: e for e in db.query(Employee).all()}
    data = [
        {
            "employee_name": employees[r.employee_id].full_name if r.employee_id in employees else None,
            "employee_code": employees[r.employee_id].employee_code if r.employee_id in employees else None,
            "attendance_date": str(r.attendance_date),
            "status": r.status,
            "is_late": r.is_late,
            "late_minutes": r.late_minutes,
            "working_minutes": r.working_minutes,
            "check_in_at": r.check_in_at.isoformat() if r.check_in_at else None,
            "check_out_at": r.check_out_at.isoformat() if r.check_out_at else None,
        } for r in rows
    ]
    if format == "csv":
        return Response(content=_csv(data, ["employee_name","employee_code","attendance_date","status","is_late","late_minutes","working_minutes","check_in_at","check_out_at"]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})
    return {"success": True, "data": data}


@router_audit.get("", response_model=dict)
def audit_logs_report(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    from app.db.models import AuditLog
    from sqlalchemy import select
    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).scalars().all()
    data = [
        {
            "id": str(r.id), "action": r.action, "entity_type": r.entity_type,
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "user_id": str(r.user_id) if r.user_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ]
    return {"success": True, "data": data}
