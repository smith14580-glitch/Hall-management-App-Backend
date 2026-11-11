from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.models import Employee, SalaryRecord, User
from app.db.session import get_db
from app.schemas.salary import SalaryUpdate

router = APIRouter(prefix="/salary", tags=["salary"])


def _dict(r: SalaryRecord) -> dict:
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


@router.get("", response_model=dict)
def list_salary_endpoint(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.query(SalaryRecord)
    if month:
        q = q.filter(SalaryRecord.month == month)
    rows = q.order_by(SalaryRecord.month.desc()).all()
    employees = {e.id: e for e in db.query(Employee).all()}
    data = []
    for r in rows:
        emp = employees.get(r.employee_id)
        data.append(
            {
                **_dict(r),
                "employee_name": emp.full_name if emp else None,
                "employee_code": emp.employee_code if emp else None,
            }
        )
    return {"success": True, "data": data}


@router.patch("/{record_id}", response_model=dict)
def update_salary_endpoint(
    record_id: UUID,
    body: SalaryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    r = db.get(SalaryRecord, record_id)
    if not r:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Salary record not found"})
    data = body.model_dump(exclude_unset=True)
    for key in ("base_amount", "paid_amount", "payment_date", "notes", "status"):
        if key in data and data[key] is not None:
            setattr(r, key, data[key])
    if "status" not in data:
        base = float(r.base_amount or 0)
        paid = float(r.paid_amount or 0)
        r.status = "paid" if base > 0 and paid >= base else ("partial" if paid > 0 else "pending")
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"success": True, "data": _dict(r), "message": "Salary record updated"}
