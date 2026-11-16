import calendar
from datetime import date
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
    delete_table_svc,
    deactivate_table_svc,
    activate_table_svc,
    table_utilization_svc,
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

@router.get("/utilization", response_model=dict)
def table_utilization_endpoint(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    hall_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    from sqlalchemy import select
    from app.db.models import Hall

    if hall_id is None:
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
        if not hall:
            return {"success": True, "data": {"month": month, "days": 0, "total_slots": 0, "booked_events": 0, "tables": []}}
        hall_id = hall.id

    target = month or date.today().strftime("%Y-%m")
    year, month_num = int(target[:4]), int(target[5:7])
    first = date(year, month_num, 1)
    last = date(year, month_num, calendar.monthrange(year, month_num)[1])
    rows = table_utilization_svc(db, hall_id, first, last)
    return {
        "success": True,
        "data": {
            "month": target,
            "days": (last - first).days + 1,
            "total_slots": ((last - first).days + 1) * 2,
            "booked_events": sum(r["booked_events"] for r in rows),
            "tables": rows,
        },
    }


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

@router.delete("/{table_id}", response_model=dict)
def delete_table_endpoint(
    table_id: UUID,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    delete_table_svc(db, table_id, force=force)
    return {"success": True, "data": {"id": str(table_id)}, "message": "Table deleted"}


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
