from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import employee as employee_crud
from app.db.models import Employee
from app.schemas.employee import EmployeeCreate


def create_employee_svc(db: Session, data: EmployeeCreate) -> Employee:
    return employee_crud.create_employee(
        db,
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        cnic=data.cnic,
        address=data.address,
        hire_date=data.hire_date,
        duty_start_time=data.duty_start_time,
        monthly_salary=data.monthly_salary,
    )


def get_employee_svc(db: Session, employee_id: UUID) -> Employee:
    e = employee_crud.get_employee(db, employee_id)
    if not e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Employee not found"})
    return e

def deactivate_employee_svc(db: Session, employee_id: UUID) -> Employee:
    e = employee_crud.deactivate_employee(db, employee_id)
    if not e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Employee not found"})
    return e

def activate_employee_svc(db: Session, employee_id: UUID) -> Employee:
    e = employee_crud.activate_employee(db, employee_id)
    if not e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Employee not found"})
    return e


def list_employees_svc(db: Session, skip: int, limit: int, search: str | None, role: str | None, is_active: bool | None):
    return employee_crud.list_employees(db, skip, limit, search, role, is_active)
