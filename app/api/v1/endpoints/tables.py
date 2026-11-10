from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User
from app.schemas.table import TableCreate, TableOut, TableAllocate
from app.services.table import (
    list_tables_svc,
    create_table_svc,
    deactivate_table_svc,
    get_allocations_svc,
    allocate_tables_svc,
    remove_allocation_svc,
)

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=dict)
def list_tables_endpoint(
    hall_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = list_tables_svc(db, hall_id)
    return {"success": True, "data": [
        {"id": str(t.id), "table_number": t.table_number, "capacity": t.capacity, "is_active": t.is_active}
        for t in rows
    ]}


@router.post("", response_model=dict)
def create_table_endpoint(
    body: TableCreate,
    hall_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    t = create_table_svc(db, hall_id, body.table_number, body.capacity)
    return {"success": True, "data": {"id": str(t.id), "table_number": t.table_number, "capacity": t.capacity}}


@router.post("/{table_id}/deactivate", response_model=dict)
def deactivate_table_endpoint(
    table_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    t = deactivate_table_svc(db, table_id)
    return {"success": True, "data": {"id": str(t.id), "is_active": t.is_active}}


@router.post("/{table_id}/activate", response_model=dict)
def activate_table_endpoint(
    table_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    t = deactivate_table_svc(db, table_id)
    t.is_active = True
    db.add(t)
    db.commit()
    return {"success": True, "data": {"id": str(t.id), "is_active": t.is_active}}
