from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import customer as customer_crud
from app.db.models import Customer
from app.schemas.customer import CustomerCreate


def create_customer_svc(db: Session, data: CustomerCreate) -> Customer:
    existing = customer_crud.find_customer_by_phone(db, data.phone)
    if existing:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_CUSTOMER", "message": "Customer with this phone already exists"})
    return customer_crud.create_customer(
        db,
        full_name=data.full_name,
        phone=data.phone,
        alternate_phone=data.alternate_phone,
        address=data.address,
        email=data.email,
        notes=data.notes,
    )


def get_customer_svc(db: Session, customer_id: UUID) -> Customer:
    c = customer_crud.get_customer(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Customer not found"})
    return c


def list_customers_svc(db: Session, skip: int, limit: int, search: str | None):
    return customer_crud.list_customers(db, skip, limit, search)
