from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crud import employee as employee_crud
from app.db.models import Employee, Role, User
from app.schemas.employee import EmployeeCreate


def create_employee_svc(db: Session, data: EmployeeCreate) -> Employee:
    password = data.password
    payload = data.model_dump(exclude={"password"})
    e = employee_crud.create_employee(db, **payload)
    if password:
        system_role = "waiter" if data.role == "waiter" else "staff"
        role = db.query(Role).filter(Role.name == system_role).first()
        if role is None:
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Role not found"})
        existing = db.query(User).filter(User.phone == data.phone).first()
        if existing is not None:
            e.user_id = existing.id
        else:
            u = User(
                role_id=role.id,
                full_name=data.full_name,
                phone=data.phone,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(u)
            db.flush()
            e.user_id = u.id
        db.add(e)
        db.commit()
        db.refresh(e)
    return e


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
