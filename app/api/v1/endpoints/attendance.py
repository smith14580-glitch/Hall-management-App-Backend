from typing import Optional
from uuid import UUID
from datetime import date
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.db.models import User, Attendance, Employee
from app.schemas.attendance import CheckInRequest, CheckOutRequest, AttendanceOut
from app.services.attendance import check_in_svc, check_out_svc, list_attendance_svc

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-in", response_model=dict)
def check_in_endpoint(
    body: CheckInRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attendance = check_in_svc(db, body.employee_id, date.today(), "manual", user)
    return {"success": True, "data": AttendanceOut.model_validate(attendance), "message": "Checked in"}


@router.post("/check-out", response_model=dict)
def check_out_endpoint(
    body: CheckOutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attendance = check_out_svc(db, body.employee_id, date.today(), user)
    return {"success": True, "data": AttendanceOut.model_validate(attendance), "message": "Checked out"}


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
    return {"success": True, "data": {"items": [AttendanceOut.model_validate(r) for r in rows], "total": total}}


@router.get("/today", response_model=dict)
def today_attendance_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = db.query(Attendance).all()
    return {"success": True, "data": [AttendanceOut.model_validate(r) for r in rows]}
