import uuid
from datetime import date, datetime, time, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import Attendance, Employee, ApplicationSetting


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.execute(select(ApplicationSetting).where(ApplicationSetting.key == key)).scalar_one_or_none()
    return row.value if row else default


def get_today_attendance(db: Session, employee_id: uuid.UUID, att_date: date) -> Optional[Attendance]:
    return db.execute(
        select(Attendance).where(Attendance.employee_id == employee_id, Attendance.attendance_date == att_date)
    ).scalar_one_or_none()


def check_in(db: Session, employee_id: uuid.UUID, att_date: date, method: str = "manual") -> Attendance:
    existing = get_today_attendance(db, employee_id, att_date)
    if existing:
        raise ValueError("DUPLICATE_CHECKIN")

    employee = db.get(Employee, employee_id)
    if not employee:
        raise ValueError("EMPLOYEE_NOT_FOUND")

    duty_start = employee.duty_start_time
    if duty_start is None:
        duty_start_str = _get_setting(db, "duty_start_time", "09:00")
        duty_start = time.fromisoformat(duty_start_str)
    grace = int(_get_setting(db, "late_grace_minutes", "15"))

    now = datetime.now(timezone.utc)
    # compute late: compare time portion in local tz (Asia/Karachi) - simplified UTC here for v1
    is_late = False
    late_minutes = None
    if now.time() > duty_start:
        # minutes past duty start
        start_dt = datetime.combine(att_date, duty_start, tzinfo=timezone.utc)
        late_minutes = int((now - start_dt).total_seconds() // 60)
        grace_dt = start_dt + timedelta(minutes=grace)
        if now > grace_dt:
            is_late = True

    row = Attendance(
        employee_id=employee_id,
        attendance_date=att_date,
        status="present",
        check_in_at=now,
        is_late=is_late,
        late_minutes=late_minutes,
        check_in_method=method,
    )
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def check_out(db: Session, employee_id: uuid.UUID, att_date: date) -> Attendance:
    row = get_today_attendance(db, employee_id, att_date)
    if not row or not row.check_in_at:
        raise ValueError("INVALID_CHECKOUT")
    if row.check_out_at:
        raise ValueError("ALREADY_CHECKED_OUT")
    now = datetime.now(timezone.utc)
    if now < row.check_in_at:
        raise ValueError("INVALID_CHECKOUT")
    row.check_out_at = now
    delta = now - row.check_in_at
    row.working_minutes = int(delta.total_seconds() // 60)
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def list_attendance(db: Session, employee_id: Optional[uuid.UUID] = None, month: Optional[str] = None, skip: int = 0, limit: int = 100):
    q = select(Attendance)
    if employee_id:
        q = q.where(Attendance.employee_id == employee_id)
    if month:
        import calendar as _cal
        y, m = int(month[:4]), int(month[5:7])
        first = date(y, m, 1)
        last = date(y, m, _cal.monthrange(y, m)[1])
        q = q.where(Attendance.attendance_date >= first, Attendance.attendance_date <= last)
    q = q.order_by(Attendance.attendance_date.desc())
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(q.offset(skip).limit(limit)).scalars().all()
    return rows, total
