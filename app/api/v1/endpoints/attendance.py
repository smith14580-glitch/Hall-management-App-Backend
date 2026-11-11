from typing import Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.db.models import User, Attendance, Employee
from app.schemas.attendance import CheckInRequest, CheckOutRequest, ScanRequest
from app.services.attendance import check_in_svc, check_out_svc, list_attendance_svc

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _att_dict(a: Attendance, employee: Employee | None = None) -> dict:
    return {
        "id": str(a.id), "employee_id": str(a.employee_id),
        "employee_name": employee.full_name if employee else None,
        "attendance_date": str(a.attendance_date), "status": a.status,
        "check_in_at": a.check_in_at.isoformat() if a.check_in_at else None,
        "check_out_at": a.check_out_at.isoformat() if a.check_out_at else None,
        "is_late": a.is_late, "late_minutes": a.late_minutes,
        "working_minutes": a.working_minutes, "check_in_method": a.check_in_method,
        "notes": a.notes,
    }


@router.post("/check-in", response_model=dict)
def check_in_endpoint(
    body: CheckInRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attendance = check_in_svc(db, body.employee_id, date.today(), "manual", user)
    emp = db.get(Employee, attendance.employee_id)
    return {"success": True, "data": _att_dict(attendance, emp), "message": "Checked in"}


@router.post("/check-out", response_model=dict)
def check_out_endpoint(
    body: CheckOutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attendance = check_out_svc(db, body.employee_id, date.today(), user)
    emp = db.get(Employee, attendance.employee_id)
    return {"success": True, "data": _att_dict(attendance, emp), "message": "Checked out"}


@router.post("/scan", response_model=dict)
def scan_attendance_endpoint(
    body: ScanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    code = body.employee_code.strip()
    emp = db.execute(select(Employee).where(Employee.employee_code == code)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Employee code not found"})
    if not emp.is_active:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Employee is inactive"})

    today = date.today()
    existing = db.execute(
        select(Attendance).where(Attendance.employee_id == emp.id, Attendance.attendance_date == today)
    ).scalar_one_or_none()

    action = body.action
    if action == "auto":
        if existing is None:
            action = "check-in"
        elif existing.check_in_at and not existing.check_out_at:
            action = "check-out"
        else:
            return {
                "success": True,
                "data": _att_dict(existing, emp),
                "message": "Aaj ki attendance mukammal hai (check-in aur check-out dono ho chuke).",
                "action": "complete",
            }

    if action == "check-in":
        row = check_in_svc(db, emp.id, today, "scan", user)
        message = f"{emp.full_name} — check-in ho gaya."
    else:
        row = check_out_svc(db, emp.id, today, user)
        message = f"{emp.full_name} — check-out ho gaya."

    return {"success": True, "data": _att_dict(row, emp), "message": message, "action": action}


@router.post("/mark", response_model=dict)
def mark_attendance_endpoint(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    employee_id = body.get("employee_id")
    att_date_raw = body.get("attendance_date") or str(date.today())
    try:
        att_date = date.fromisoformat(str(att_date_raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Invalid attendance_date"})
    status = body.get("status") or "present"
    if status not in ("present", "absent", "leave", "half_day"):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Invalid status"})
    if not employee_id:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "employee_id required"})
    from uuid import UUID as _UUID
    try:
        emp_uuid = _UUID(str(employee_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Invalid employee_id"})
    emp = db.get(Employee, emp_uuid)
    if not emp:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Employee not found"})
    existing = db.execute(
        select(Attendance).where(Attendance.employee_id == emp_uuid, Attendance.attendance_date == att_date)
    ).scalar_one_or_none()
    if existing:
        existing.status = status
        row = existing
    else:
        row = Attendance(employee_id=emp_uuid, attendance_date=att_date, status=status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "data": _att_dict(row, emp), "message": f"Marked {status}"}


@router.get("/me", response_model=dict)
def my_attendance_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    month: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    emp = db.execute(select(Employee).where(Employee.user_id == user.id)).scalar_one_or_none()
    rows, total = list_attendance_svc(db, emp.id if emp else user.id, month, skip, limit)
    return {"success": True, "data": [_att_dict(r, emp) for r in rows]}


@router.get("/today", response_model=dict)
def today_attendance_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = db.query(Attendance).filter(Attendance.attendance_date == date.today()).all()
    employees = {e.id: e for e in db.query(Employee).all()}
    return {"success": True, "data": [_att_dict(r, employees.get(r.employee_id)) for r in rows]}


@router.get("", response_model=dict)
def list_attendance_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
    month: Optional[str] = Query(None),
    employee_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    rows, total = list_attendance_svc(db, employee_id, month, skip, limit)
    employees = {e.id: e for e in db.query(Employee).all()}
    return {"success": True, "data": [_att_dict(r, employees.get(r.employee_id)) for r in rows]}
