import uuid
from typing import Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.db.models import Customer


def create_customer(db: Session, **data) -> Customer:
    c = Customer(**data)
    db.add(c)
    db.flush()
    db.commit()
    db.refresh(c)
    return c


def get_customer(db: Session, customer_id: uuid.UUID) -> Optional[Customer]:
    return db.get(Customer, customer_id)


def find_customer_by_phone(db: Session, phone: str) -> Optional[Customer]:
    return db.execute(select(Customer).where(Customer.phone == phone)).scalar_one_or_none()


def list_customers(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> Tuple[list[Customer], int]:
    q = select(Customer)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Customer.full_name.ilike(like), Customer.phone.ilike(like)))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    q = q.order_by(Customer.created_at.desc()).offset(skip).limit(limit)
    rows = db.execute(q).scalars().all()
    return rows, total
