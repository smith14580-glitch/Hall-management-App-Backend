from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.models import ApplicationSetting, Hall, Quotation, QuotationSettings, User
from app.db.session import get_db
from app.schemas.quotation import (
    QuotationCreate,
    QuotationTemplateOut,
    QuotationTemplateUpdate,
)

router = APIRouter(prefix="/quotations", tags=["quotations"])

DEFAULT_FACILITIES = (
    "- Fully air-conditioned, climate-controlled hall\n"
    "- Beautifully decorated stage with seating for the couple\n"
    "- Bridal room with attached washroom\n"
    "- Premium chairs and tables\n"
    "- Buffet stations with professional service staff\n"
    "- Ample parking space for guests"
)
DEFAULT_CHARGEABLE = "Cold drinks, mineral water, extra floral work, table service, extra time, etc."
DEFAULT_POLICIES = (
    "- If you wish to postpone your event, you may select a new date subject to the prevailing rates, "
    "and the paid advance amount will be adjusted.\n"
    "- If you cancel your event on the scheduled booking date, the advance amount is non-refundable."
)
DEFAULT_TEMPLATE = (
    "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ\n\n"
    "Dear {{client_name}},\n\n"
    "Welcome to MARQUE ONE, where extraordinary moments become lasting memories.\n"
    "We are thrilled to partner with you in crafting an unforgettable celebration.\n"
    "Here are your event details:\n"
    "- Enquiry Date: {{enquiry_date}}\n"
    "- Enquiry #: {{enquiry_no}}\n"
    "- Client Reach: {{source}}\n"
    "- Event Type: {{event_type}}\n"
    "- Event Date: {{event_date}}\n"
    "- Guest Count: {{guest_count}}\n"
    "- Banquet Hall: {{hall_name}}\n"
    "- Package Price: {{package_price}} ({{slot}} slot)\n"
    "- Advance Required: {{advance_percent}}% to confirm your booking\n\n"
    "Event Timings:\n"
    "- Day Slot: 12:00 PM – 4:00 PM\n"
    "- Night Slot: 7:00 PM – 11:00 PM\n\n"
    "Venue Facilities & Setup:\n{{facilities}}\n\n"
    "Chargeable Items:\n{{chargeable_items}}\n\n"
    "For Confirmation of Booking:\n"
    "- A {{advance_percent}}% advance deposit is required to secure your booking. "
    "Payment can be made via cash or online bank transfer.\n\n"
    "Advance Amount Refund & Adjustment Policy:\n{{policies}}\n\n"
    "Office Timings: {{office_timings}}\n\n"
    "Should you require further information or assistance, please contact your dedicated Event Manager, "
    "{{manager_name}} — {{manager_phone}}.\n\n"
    "Location: {{location_link}}\n\n"
    "Best Regards,\nMARQUE ONE\n\n"
    "Note: This quotation is valid for 7 days (until {{valid_until}}). After that, rates may change."
)


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.execute(select(ApplicationSetting).where(ApplicationSetting.key == key)).scalar_one_or_none()
    return row.value if row else default


def _settings_row(db: Session) -> QuotationSettings:
    row = db.execute(select(QuotationSettings).limit(1)).scalar_one_or_none()
    if row is None:
        row = QuotationSettings(
            template_body=DEFAULT_TEMPLATE,
            facilities=DEFAULT_FACILITIES,
            chargeable_items=DEFAULT_CHARGEABLE,
            policies=DEFAULT_POLICIES,
            validity_days=7,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _fmt_date(d: Optional[date]) -> str:
    if not d:
        return ""
    return d.strftime("%d %b %Y")


def _fmt_money(v) -> str:
    if v is None:
        return ""
    try:
        return "PKR {:,.0f}".format(float(v))
    except Exception:
        return str(v)


def _render_template(tpl: QuotationSettings, ctx: dict) -> str:
    body = tpl.template_body or DEFAULT_TEMPLATE
    facilities = tpl.facilities if tpl.facilities is not None else DEFAULT_FACILITIES
    chargeable = tpl.chargeable_items if tpl.chargeable_items is not None else DEFAULT_CHARGEABLE
    policies = tpl.policies if tpl.policies is not None else DEFAULT_POLICIES
    values = {
        "client_name": ctx.get("client_name") or "",
        "enquiry_no": ctx.get("enquiry_no") or "",
        "enquiry_date": ctx.get("enquiry_date") or "",
        "source": ctx.get("source") or "",
        "event_type": ctx.get("event_type") or "",
        "event_date": ctx.get("event_date") or "",
        "slot": ctx.get("slot") or "",
        "guest_count": "" if ctx.get("guest_count") is None else str(ctx.get("guest_count")),
        "hall_name": ctx.get("hall_name") or "",
        "package_price": ctx.get("package_price") or "",
        "advance_percent": "" if ctx.get("advance_percent") is None else str(ctx.get("advance_percent")),
        "valid_until": ctx.get("valid_until") or "",
        "manager_name": tpl.manager_name or "",
        "manager_phone": tpl.manager_phone or "",
        "office_timings": tpl.office_timings or "",
        "location_link": tpl.location_link or "",
        "facilities": facilities,
        "chargeable_items": chargeable,
        "policies": policies,
    }
    out = body
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", str(val))
    return out


def _normalize_phone(phone: str) -> str:
    p = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0"):
        p = "92" + p[1:]
    if p.startswith("00"):
        p = p[2:]
    return p


def _next_enquiry_no(db: Session) -> str:
    year = date.today().year
    prefix = f"QT-{year}-"
    rows = db.execute(select(Quotation.enquiry_no).where(Quotation.enquiry_no.like(f"{prefix}%"))).scalars().all()
    nums = []
    for r in rows:
        try:
            nums.append(int(str(r).split("-")[-1]))
        except (ValueError, AttributeError):
            continue
    nxt = (max(nums) if nums else 0) + 1
    return f"{prefix}{nxt:04d}"


def _to_out(q: Quotation, whatsapp_url: Optional[str] = None) -> dict:
    return {
        "id": str(q.id),
        "enquiry_no": q.enquiry_no,
        "client_name": q.client_name,
        "client_phone": q.client_phone,
        "source": q.source,
        "event_type": q.event_type,
        "event_date": q.event_date,
        "slot": q.slot,
        "guest_count": q.guest_count,
        "hall_id": str(q.hall_id) if q.hall_id else None,
        "hall_name": None,
        "package_price": float(q.package_price) if q.package_price is not None else None,
        "advance_percent": q.advance_percent,
        "message_body": q.message_body,
        "status": q.status,
        "valid_until": q.valid_until,
        "sent_at": q.sent_at,
        "created_at": q.created_at,
        "whatsapp_url": whatsapp_url,
    }


@router.get("/template", response_model=dict)
def get_template(db: Session = Depends(get_db), user: User = Depends(require_role("super_admin"))):
    tpl = _settings_row(db)
    hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
    return {
        "success": True,
        "data": {
            "template": QuotationTemplateOut(
                template_body=tpl.template_body,
                facilities=tpl.facilities,
                chargeable_items=tpl.chargeable_items,
                policies=tpl.policies,
                office_timings=tpl.office_timings,
                manager_name=tpl.manager_name,
                manager_phone=tpl.manager_phone,
                location_link=tpl.location_link,
                validity_days=tpl.validity_days,
                updated_at=tpl.updated_at,
            ).model_dump(),
            "hall": {"id": str(hall.id), "name": hall.name} if hall else None,
        },
    }


@router.put("/template", response_model=dict)
def update_template(
    body: QuotationTemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    tpl = _settings_row(db)
    data = body.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(tpl, key, val)
    tpl.updated_by = user.id
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return {"success": True, "data": QuotationTemplateOut(
        template_body=tpl.template_body,
        facilities=tpl.facilities,
        chargeable_items=tpl.chargeable_items,
        policies=tpl.policies,
        office_timings=tpl.office_timings,
        manager_name=tpl.manager_name,
        manager_phone=tpl.manager_phone,
        location_link=tpl.location_link,
        validity_days=tpl.validity_days,
        updated_at=tpl.updated_at,
    ).model_dump(), "message": "Template saved"}


@router.post("", response_model=dict)
def create_quotation(
    body: QuotationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    tpl = _settings_row(db)
    hall = None
    if body.hall_id:
        hall = db.get(Hall, body.hall_id)
    if hall is None:
        hall = db.execute(select(Hall).where(Hall.is_active == True).limit(1)).scalar_one_or_none()  # noqa: E712
    if hall is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Hall not found"})

    slot = body.slot or ""
    if slot == "day":
        package_price = float(hall.day_price)
    elif slot == "night":
        package_price = float(hall.night_price)
    else:
        package_price = None

    advance_percent = int(_get_setting(db, "default_advance_percent", "50"))
    try:
        advance_percent = int(advance_percent)
    except Exception:
        advance_percent = 50

    enquiry_no = _next_enquiry_no(db)
    today = date.today()
    validity_days = tpl.validity_days or 7
    valid_until = today + timedelta(days=validity_days)

    ctx = {
        "client_name": body.client_name,
        "enquiry_no": enquiry_no,
        "enquiry_date": _fmt_date(today),
        "source": body.source or "",
        "event_type": body.event_type or "",
        "event_date": _fmt_date(body.event_date),
        "slot": slot,
        "guest_count": body.guest_count,
        "hall_name": hall.name,
        "package_price": _fmt_money(package_price) if package_price is not None else "",
        "advance_percent": advance_percent,
        "valid_until": _fmt_date(valid_until),
    }
    message_body = _render_template(tpl, ctx)

    q = Quotation(
        enquiry_no=enquiry_no,
        client_name=body.client_name,
        client_phone=body.client_phone,
        source=body.source,
        event_type=body.event_type,
        event_date=body.event_date,
        slot=slot or None,
        guest_count=body.guest_count,
        hall_id=hall.id,
        package_price=package_price,
        advance_percent=advance_percent,
        message_body=message_body,
        status="draft",
        valid_until=valid_until,
        created_by=user.id,
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    phone = _normalize_phone(body.client_phone)
    url = f"https://wa.me/{phone}?text={quote(message_body, safe='')}"
    out = _to_out(q, whatsapp_url=url)
    out["hall_name"] = hall.name
    return {"success": True, "data": out, "message": "Quotation created"}


@router.get("", response_model=dict)
def list_quotations(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.query(Quotation)
    if status:
        q = q.filter(Quotation.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Quotation.client_name.ilike(like))
            | (Quotation.client_phone.ilike(like))
            | (Quotation.enquiry_no.ilike(like))
        )
    rows = q.order_by(Quotation.created_at.desc()).all()
    halls = {str(h.id): h.name for h in db.query(Hall).all()}
    data = []
    for r in rows:
        out = _to_out(r)
        out["hall_name"] = halls.get(str(r.hall_id)) if r.hall_id else None
        data.append(out)
    return {"success": True, "data": data}


@router.get("/{quotation_id}", response_model=dict)
def get_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.get(Quotation, quotation_id)
    if not q:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Quotation not found"})
    halls = {str(h.id): h.name for h in db.query(Hall).all()}
    out = _to_out(q)
    out["hall_name"] = halls.get(str(q.hall_id)) if q.hall_id else None
    # rebuild whatsapp url
    phone = _normalize_phone(q.client_phone)
    if q.message_body:
        out["whatsapp_url"] = f"https://wa.me/{phone}?text={quote(q.message_body, safe='')}"
    return {"success": True, "data": out}


@router.patch("/{quotation_id}/sent", response_model=dict)
def mark_sent(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("super_admin")),
):
    q = db.get(Quotation, quotation_id)
    if not q:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Quotation not found"})
    q.status = "sent"
    q.sent_at = datetime.now()
    db.add(q)
    db.commit()
    db.refresh(q)
    halls = {str(h.id): h.name for h in db.query(Hall).all()}
    out = _to_out(q)
    out["hall_name"] = halls.get(str(q.hall_id)) if q.hall_id else None
    return {"success": True, "data": out, "message": "Marked as sent"}