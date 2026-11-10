from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.crud import notification as notification_crud


def list_notifications_svc(db: Session, user_id: UUID, unread_only: bool, skip: int, limit: int):
    return notification_crud.list_notifications(db, user_id, unread_only, skip, limit)


def mark_read_svc(db: Session, notification_id: UUID, user_id: UUID):
    n = notification_crud.mark_read(db, notification_id, user_id)
    if not n:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Notification not found"})
    return n


def mark_all_read_svc(db: Session, user_id: UUID) -> int:
    return notification_crud.mark_all_read(db, user_id)


def unread_count_svc(db: Session, user_id: UUID) -> int:
    return notification_crud.unread_count(db, user_id)
