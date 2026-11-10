from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User
from app.schemas.notification import NotificationOut
from app.services.notification import list_notifications_svc, mark_read_svc, mark_all_read_svc, unread_count_svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=dict)
def list_notifications_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    rows, total = list_notifications_svc(db, user.id, unread_only, skip, limit)
    return {"success": True, "data": {"items": [NotificationOut.model_validate(n) for n in rows], "total": total}}


@router.post("/{notification_id}/read", response_model=dict)
def mark_read_endpoint(
    notification_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    n = mark_read_svc(db, notification_id, user.id)
    return {"success": True, "data": NotificationOut.model_validate(n), "message": "Marked read"}


@router.post("/read-all", response_model=dict)
def mark_all_read_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    n = mark_all_read_svc(db, user.id)
    return {"success": True, "data": {"count": n}, "message": "All marked read"}


@router.get("/unread-count", response_model=dict)
def unread_count_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = unread_count_svc(db, user.id)
    return {"success": True, "data": {"count": c}}
