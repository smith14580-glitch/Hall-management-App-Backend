from sqlalchemy import select
from uuid import UUID
from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import attendance as attendance_crud
from app.db.models import Attendance, Employee


def _resolve_employee_id(db: Session, employee_id: UUID | None, current_user) -> UUID:
    if employee_id:
        return employee_id
    emp = db.execute(select(Employee).where(Employee.user_id == current_user.id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "No employee record linked to this account"})
    return emp.id


def check_in_svc(db: Session, employee_id: UUID | None, att_date: date, method: str, current_user) -> Attendance:
    target = _resolve_employee_id(db, employee_id, current_user)
    try:
        return attendance_crud.check_in(db, target, att_date, method)
    except ValueError as e:
        if str(e) == "DUPLICATE_CHECKIN":
            raise HTTPException(status_code=409, detail={"code": "DUPLICATE_CHECKIN", "message": "Already checked in today"})
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})


def check_out_svc(db: Session, employee_id: UUID | None, att_date: date, current_user) -> Attendance:
    target = _resolve_employee_id(db, employee_id, current_user)
    try:
        return attendance_crud.check_out(db, target, att_date)
    except ValueError as e:
        if str(e) in ("INVALID_CHECKOUT", "ALREADY_CHECKED_OUT"):
            raise HTTPException(status_code=409, detail={"code": "INVALID_CHECKOUT", "message": str(e)})
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})


def list_attendance_svc(db: Session, employee_id: UUID | None, month: str | None, skip: int, limit: int):
    return attendance_crud.list_attendance(db, employee_id, month, skip, limit)
