from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Table as TableModel
from app.schemas.table import TableCreate
from app.services.table import (
    list_tables_svc,
    create_table_svc,
    deactivate_table_svc,
    activate_table_svc,
)

router = APIRouter(prefix="/tables", tags=["tables"])

def _table_dict(t) -> dict:
    return {
        "id": str(t.id),
        "hall_id": str(t.hall_id),
        "table_number": t.table_number,
        "capacity": t.capacity,
        "is_active": t.is_active,
    }

@router.get("", response_model=dict)
def list_tables_endpoint(
    hall_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    if hall_id is None:
        from sqlalchemy import select
        from app.db.models import Hall
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
        if not hall:
            return {"success": True, "data": []}
        hall_id = hall.id
    rows = list_tables_svc(db, hall_id)
    return {"success": True, "data": [_table_dict(t) for t in rows]}

@router.post("", response_model=dict)
def create_table_endpoint(
    body: TableCreate,
    hall_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    if hall_id is None:
        from sqlalchemy import select
        from app.db.models import Hall
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
        if not hall:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Hall not found"})
        hall_id = hall.id
    t = create_table_svc(db, hall_id, body.table_number, body.capacity)
    return {"success": True, "data": _table_dict(t), "message": "Table created"}

@router.post("/{table_id}/deactivate", response_model=dict)
def deactivate_table_endpoint(
    table_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    t = deactivate_table_svc(db, table_id)
    return {"success": True, "data": _table_dict(t), "message": "Table deactivated"}

@router.post("/{table_id}/activate", response_model=dict)
def activate_table_endpoint(
    table_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    t = activate_table_svc(db, table_id)
    return {"success": True, "data": _table_dict(t), "message": "Table activated"}

@router.patch("/{table_id}", response_model=dict)
def update_table_endpoint(
    table_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    t = db.get(TableModel, table_id)
    if not t:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Table not found"})
    for key in ("table_number", "capacity", "is_active"):
        if key in body and body[key] is not None:
            setattr(t, key, body[key])
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"success": True, "data": _table_dict(t), "message": "Table updated"}
