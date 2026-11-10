import uuid
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Notification


def create_notification(db: Session, user_id: uuid.UUID, type: str, title: str, body: str | None = None, related_booking_id: uuid.UUID | None = None, related_employee_id: uuid.UUID | None = None) -> Notification:
    n = Notification(
        user_id=user_id, type=type, title=title, body=body,
        related_booking_id=related_booking_id, related_employee_id=related_employee_id,
    )
    db.add(n)
    db.flush()
    db.commit()
    db.refresh(n)
    return n


def list_notifications(db: Session, user_id: uuid.UUID, unread_only: bool = False, skip: int = 0, limit: int = 50):
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc())
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(q.offset(skip).limit(limit)).scalars().all()
    return rows, total


def mark_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
    n = db.execute(select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)).scalar_one_or_none()
    if not n:
        return None
    n.is_read = True
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    rows = db.execute(select(Notification).where(Notification.user_id == user_id, Notification.is_read == False)).scalars().all()  # noqa
    for n in rows:
        n.is_read = True
    db.commit()
    return len(rows)


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return db.execute(select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read == False)).scalar() or 0  # noqa
