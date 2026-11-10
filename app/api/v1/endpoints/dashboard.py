from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, ApplicationSetting
from app.schemas.dashboard import SettingUpdate, SettingOut
from app.services.dashboard import dashboard_summary, list_settings, get_setting, set_setting

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=dict)
def dashboard_summary_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    data = dashboard_summary(db)
    return {"success": True, "data": data}


@router.get("/revenue", response_model=dict)
def dashboard_revenue_endpoint(
    period: str = Query("monthly", pattern="^(daily|weekly|monthly|annual)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    from sqlalchemy import func, select
    from app.db.models import Payment
    fmt = {"daily": "%Y-%m-%d", "weekly": "%Y-%W", "monthly": "%Y-%m", "annual": "%Y"}[period]
    rows = db.execute(
        select(Payment.payment_date, func.sum(Payment.amount))
        .where(Payment.is_voided == False)  # noqa: E712
        .group_by(func.to_char(Payment.payment_date, fmt), Payment.payment_date)
        .order_by(Payment.payment_date.asc())
    ).all()
    series = [
        {"period": str(r[0]), "date": str(r[0]), "total": float(r[1]), "revenue": float(r[1]), "count": 0}
        for r in rows
    ]
    return {"success": True, "data": series}


router_settings = APIRouter(prefix="/settings", tags=["settings"])


@router_settings.get("", response_model=dict)
def list_settings_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    rows = list_settings(db)
    return {"success": True, "data": [
        {"key": r.key, "value": r.value, "description": r.description} for r in rows
    ]}


@router_settings.patch("/{key}", response_model=dict)
def update_setting_endpoint(
    key: str,
    body: SettingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    r = set_setting(db, key, body.value, user.id)
    return {"success": True, "data": {"key": r.key, "value": r.value}, "message": "Setting updated"}
