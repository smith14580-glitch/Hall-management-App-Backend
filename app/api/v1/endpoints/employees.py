from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User
from app.schemas.employee import EmployeeCreate, EmployeeOut
from app.services.employee import create_employee_svc, get_employee_svc, list_employees_svc

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=dict)
def create_employee_endpoint(
    body: EmployeeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    try:
        e = create_employee_svc(db, body)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    return {"success": True, "data": EmployeeOut.model_validate(e), "message": "Employee created"}


@router.get("", response_model=dict)
def list_employees_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    rows, total = list_employees_svc(db, skip, limit, search, role, is_active)
    return {
        "success": True,
        "data": {
            "items": [EmployeeOut.model_validate(e) for e in rows],
            "total": total,
        },
    }


@router.get("/{employee_id}", response_model=dict)
def get_employee_endpoint(
    employee_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    e = get_employee_svc(db, employee_id)
    return {"success": True, "data": EmployeeOut.model_validate(e)}
