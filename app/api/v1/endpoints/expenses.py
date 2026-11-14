import calendar
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.db.models import Expense, User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _expense_dict(e: Expense) -> dict:
    return {
        "id": str(e.id),
        "category": e.category,
        "vendor": e.vendor,
        "description": e.description,
        "amount": float(e.amount),
        "expense_date": str(e.expense_date),
        "reference": e.reference,
        "notes": e.notes,
        "created_by": str(e.created_by) if e.created_by else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _month_bounds(month: str) -> tuple[date, date]:
    y, m = int(month[:4]), int(month[5:7])
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


@router.get("", response_model=dict)
def list_expenses_endpoint(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    category: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    format: str = Query("json"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.query(Expense)
    if month:
        first, last = _month_bounds(month)
        q = q.filter(Expense.expense_date >= first, Expense.expense_date <= last)
    if date_from:
        q = q.filter(Expense.expense_date >= date_from)
    if date_to:
        q = q.filter(Expense.expense_date <= date_to)
    if category:
        q = q.filter(Expense.category == category)
    rows = q.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).all()
    items = [_expense_dict(e) for e in rows]
    by_category: dict[str, float] = {}
    for e in rows:
        by_category[e.category] = by_category.get(e.category, 0.0) + float(e.amount)
    total = sum(float(e.amount) for e in rows)

    if format == "csv":
        import csv
        import io

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["date", "category", "vendor", "description", "amount", "reference", "notes"])
        for e in items:
            w.writerow([
                e["expense_date"], e["category"], e["vendor"] or "", e["description"],
                e["amount"], e["reference"] or "", e["notes"] or "",
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )

    return {
        "success": True,
        "data": {"items": items, "total": total, "by_category": by_category, "count": len(items)},
    }


@router.post("", response_model=dict, status_code=201)
def create_expense_endpoint(
    body: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    exp = Expense(**body.model_dump(), created_by=user.id)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {"success": True, "data": _expense_dict(exp), "message": "Expense added"}


@router.patch("/{expense_id}", response_model=dict)
def update_expense_endpoint(
    expense_id: UUID,
    body: ExpenseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    exp = db.get(Expense, expense_id)
    if not exp:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Expense not found"})
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(exp, key, value)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {"success": True, "data": _expense_dict(exp), "message": "Expense updated"}


@router.delete("/{expense_id}", response_model=dict)
def delete_expense_endpoint(
    expense_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    exp = db.get(Expense, expense_id)
    if not exp:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Expense not found"})
    db.delete(exp)
    db.commit()
    return {"success": True, "data": None, "message": "Expense deleted"}
