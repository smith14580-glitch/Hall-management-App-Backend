from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User
from app.schemas.dashboard import SettingUpdate
from app.services.dashboard import dashboard_summary, list_settings, set_setting

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
    from datetime import date as _date

    fmt = {"daily": "%Y-%m-%d", "weekly": "%Y-%W", "monthly": "%Y-%m", "annual": "%Y"}[period]
    _date.today()
    rows = db.execute(
        select(Payment.payment_date, func.sum(Payment.amount))
        .where(Payment.is_voided == False)  # noqa: E712
        .group_by(func.to_char(Payment.payment_date, fmt), Payment.payment_date)
        .order_by(Payment.payment_date.asc())
    ).all()

    # Frontend expects RevenuePoint { label, revenue }; keep the most
    # recent ~12 buckets so the chart stays readable.
    buckets: dict[str, float] = {}
    for payment_date, total in rows:
        key = payment_date.strftime(fmt)
        buckets[key] = float(total)
    series = [
        {"label": key, "revenue": value, "date": key, "total": value, "count": 0}
        for key, value in sorted(buckets.items())
    ][-12:]
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
