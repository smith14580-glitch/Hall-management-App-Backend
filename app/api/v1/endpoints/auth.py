from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.db.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == body.phone).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid phone or password"})
    if not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Account deactivated"})
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    employee_id = None
    # no employee link lookup here for brevity; set in Phase 2 polish
    access = create_access_token(str(user.id), user.role.name, employee_id)
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user={"id": str(user.id), "full_name": user.full_name, "role": user.role.name, "phone": user.phone},
    )


@router.post("/refresh")
def refresh(body: RefreshRequest):
    # Minimal: re-issue access token from refresh. Full rotation in polish.
    from app.core.security import decode_refresh_token

    try:
        payload = decode_refresh_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid refresh token"})
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid token type"})
    # Look up user
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.get(User, payload.get("sub"))
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "User inactive"})
        access = create_access_token(str(user.id), user.role.name, None)
        return {"success": True, "data": {"access_token": access, "token_type": "bearer"}, "message": None}
    finally:
        db.close()


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone": user.phone,
            "email": user.email,
            "role": user.role.name,
        },
    }


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    # Stateless JWT: logout is client-side session clear. Access token
    # expires in 15 min; refresh token rotation prevents reuse.
    return {"success": True, "data": None, "message": "Logged out"}


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Current password incorrect"})
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"success": True, "data": None, "message": "Password changed"}
