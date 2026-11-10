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
