from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import User, SalaryRecord
from app.schemas.employee import EmployeeCreate, EmployeeOut
from app.schemas.salary import SalaryCreate
from app.services.employee import create_employee_svc, get_employee_svc, list_employees_svc, deactivate_employee_svc, activate_employee_svc

router = APIRouter(prefix="/employees", tags=["employees"])


def _salary_status(base: float, paid: float) -> str:
    if base > 0 and paid >= base:
        return "paid"
    if paid > 0:
        return "partial"
    return "pending"


def _salary_dict(r: SalaryRecord) -> dict:
    return {
        "id": str(r.id),
        "employee_id": str(r.employee_id),
        "month": r.month,
        "base_amount": float(r.base_amount or 0),
        "paid_amount": float(r.paid_amount or 0),
        "balance": float((r.base_amount or 0) - (r.paid_amount or 0)),
        "payment_date": str(r.payment_date) if r.payment_date else None,
        "status": r.status,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


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

@router.patch("/{employee_id}", response_model=dict)
def update_employee_endpoint(
    employee_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    e = get_employee_svc(db, employee_id)
    for key in ("full_name", "phone", "role", "is_active", "address", "monthly_salary"):
        if key in body and body[key] is not None:
            setattr(e, key, body[key])
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"success": True, "data": EmployeeOut.model_validate(e), "message": "Employee updated"}

@router.post("/{employee_id}/deactivate", response_model=dict)
def deactivate_employee_endpoint(
    employee_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    e = deactivate_employee_svc(db, employee_id)
    return {"success": True, "data": EmployeeOut.model_validate(e), "message": "Employee deactivated"}

@router.post("/{employee_id}/activate", response_model=dict)
def activate_employee_endpoint(
    employee_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    e = activate_employee_svc(db, employee_id)
    return {"success": True, "data": EmployeeOut.model_validate(e), "message": "Employee activated"}


@router.get("/{employee_id}/salary", response_model=dict)
def list_employee_salary_endpoint(
    employee_id: UUID,
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    get_employee_svc(db, employee_id)
    q = db.query(SalaryRecord).filter(SalaryRecord.employee_id == employee_id)
    if month:
        q = q.filter(SalaryRecord.month == month)
    rows = q.order_by(SalaryRecord.month.desc()).all()
    return {"success": True, "data": [_salary_dict(r) for r in rows]}


@router.post("/{employee_id}/salary", response_model=dict)
def upsert_employee_salary_endpoint(
    employee_id: UUID,
    body: SalaryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    get_employee_svc(db, employee_id)
    row = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee_id, SalaryRecord.month == body.month)
        .first()
    )
    base = float(body.base_amount)
    paid = float(body.paid_amount or 0)
    if row is None:
        row = SalaryRecord(
            employee_id=employee_id,
            month=body.month,
            base_amount=body.base_amount,
            paid_amount=body.paid_amount or 0,
            payment_date=body.payment_date,
            notes=body.notes,
            status=_salary_status(base, paid),
            created_by=user.id,
        )
        db.add(row)
    else:
        row.base_amount = body.base_amount
        row.paid_amount = body.paid_amount or 0
        row.payment_date = body.payment_date
        row.notes = body.notes
        row.status = _salary_status(base, paid)
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "data": _salary_dict(row), "message": "Salary record saved"}
