from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, Hall

router = APIRouter(prefix="/halls", tags=["halls"])
router_pricing = APIRouter(prefix="/pricing", tags=["halls"])


def _hall_dict(h: Hall) -> dict:
    return {
        "id": str(h.id), "name": h.name,
        "capacity_guests": h.capacity_guests, "capacity_tables": h.capacity_tables,
        "day_price": float(h.day_price), "night_price": float(h.night_price),
        "is_active": h.is_active,
    }


@router.get("", response_model=dict)
def list_halls(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = db.execute(select(Hall).order_by(Hall.name)).scalars().all()
    return {"success": True, "data": [_hall_dict(h) for h in rows]}


@router.get("/{hall_id}", response_model=dict)
def get_hall(
    hall_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    h = db.get(Hall, hall_id)
    if not h:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Hall not found"}}
    return {"success": True, "data": _hall_dict(h)}


@router.patch("/{hall_id}", response_model=dict)
def update_hall(
    hall_id: str,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    h = db.get(Hall, hall_id)
    if not h:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Hall not found"}}
    for key in ("name", "capacity_guests", "capacity_tables", "day_price", "night_price", "is_active"):
        if key in body and body[key] is not None:
            setattr(h, key, body[key])
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"success": True, "data": _hall_dict(h), "message": "Hall updated"}


@router_pricing.get("/current", response_model=dict)
def current_pricing(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    h = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
    if not h:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Hall not found"}}
    return {
        "success": True,
        "data": {
            "hall_id": str(h.id), "hall_name": h.name,
            "day_price": float(h.day_price), "night_price": float(h.night_price),
        },
    }
