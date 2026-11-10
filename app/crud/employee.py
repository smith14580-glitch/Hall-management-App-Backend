import uuid
from typing import Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.db.models import Employee


def next_employee_code(db: Session) -> str:
    row = db.execute(select(func.max(Employee.employee_code))).scalar()
    n = 0
    if row:
        try:
            n = int(str(row).split("-")[-1])
        except Exception:
            n = 0
    return f"EMP-{n + 1:04d}"


def create_employee(db: Session, **data) -> Employee:
    data["employee_code"] = next_employee_code(db)
    e = Employee(**data)
    db.add(e)
    db.flush()
    db.commit()
    db.refresh(e)
    return e


def get_employee(db: Session, employee_id: uuid.UUID) -> Optional[Employee]:
    return db.get(Employee, employee_id)

def deactivate_employee(db: Session, employee_id: uuid.UUID) -> Optional[Employee]:
    e = db.get(Employee, employee_id)
    if not e:
        return None
    e.is_active = False
    db.add(e)
    db.commit()
    db.refresh(e)
    return e

def activate_employee(db: Session, employee_id: uuid.UUID) -> Optional[Employee]:
    e = db.get(Employee, employee_id)
    if not e:
        return None
    e.is_active = True
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def list_employees(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> Tuple[list[Employee], int]:
    q = select(Employee)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Employee.full_name.ilike(like), Employee.phone.ilike(like), Employee.employee_code.ilike(like)))
    if role:
        q = q.where(Employee.role == role)
    if is_active is not None:
        q = q.where(Employee.is_active == is_active)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    q = q.order_by(Employee.created_at.desc()).offset(skip).limit(limit)
    rows = db.execute(q).scalars().all()
    return rows, total
