from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise unauthorized()
    try:
        payload = decode_access_token(creds.credentials)
    except Exception:
        raise unauthorized("Invalid or expired token")
    if payload.get("type") != "access":
        raise unauthorized()
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise unauthorized("User not found or inactive")
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        role_name = user.role.name if user.role else None
        if role_name not in roles:
            raise forbidden()
        return user

    return checker
