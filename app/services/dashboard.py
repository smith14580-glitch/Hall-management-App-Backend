from datetime import date
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.db.models import Booking, Payment, Customer, Employee, Attendance, ApplicationSetting, Hall


def get_setting(db: Session, key: str) -> str | None:
    row = db.execute(
        select(ApplicationSetting).where(ApplicationSetting.key == key)
    ).scalar_one_or_none()
    return row.value if row else None


def set_setting(db: Session, key: str, value: str, updated_by):
    row = db.execute(
        select(ApplicationSetting).where(ApplicationSetting.key == key)
    ).scalar_one_or_none()
    if row:
        row.value = value
        row.updated_by = updated_by
    else:
        row = ApplicationSetting(key=key, value=value, updated_by=updated_by)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_settings(db: Session):
    return db.execute(select(ApplicationSetting).order_by(ApplicationSetting.key)).scalars().all()


def dashboard_summary(db: Session) -> dict:
    today = date.today()
    total_bookings = db.execute(select(func.count(Booking.id))).scalar() or 0
    confirmed = db.execute(select(func.count(Booking.id)).where(Booking.status == "confirmed")).scalar() or 0
    pending = db.execute(select(func.count(Booking.id)).where(Booking.status == "pending")).scalar() or 0
    cancelled = db.execute(select(func.count(Booking.id)).where(Booking.status == "cancelled")).scalar() or 0
    today_events = db.execute(
        select(func.count(Booking.id)).where(Booking.event_date == today)
    ).scalar() or 0
    total_customers = db.execute(select(func.count(Customer.id))).scalar() or 0
    total_employees = db.execute(select(func.count(Employee.id))).scalar() or 0
    present_today = db.execute(
        select(func.count(Attendance.id)).where(Attendance.attendance_date == today, Attendance.status == "present")
    ).scalar() or 0

    paid = db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.is_voided == False)).scalar() or 0  # noqa
    total_revenue = float(paid)

    outstanding = db.execute(
        select(func.coalesce(func.sum(Booking.balance_amount), 0)).where(Booking.balance_amount > 0)
    ).scalar() or 0

    return {
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed,
        "pending_bookings": pending,
        "cancelled_bookings": cancelled,
        "total_revenue": total_revenue,
        "total_outstanding": float(outstanding),
        "today_events": today_events,
        "total_customers": total_customers,
        "total_employees": total_employees,
        "present_today": present_today,
    }
