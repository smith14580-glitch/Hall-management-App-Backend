import os
import sys
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, Base, engine
from app.db.models import Role, User, Hall, ApplicationSetting, Employee

Base.metadata.create_all(bind=engine)


def seed(db: Session) -> None:
    # roles
    role_names = ["super_admin", "staff", "waiter"]
    for i, name in enumerate(role_names, start=1):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(id=i, name=name, description=name))
    db.commit()

    # hall
    if not db.query(Hall).filter(Hall.name == "MARQUE ONE").first():
        db.add(
            Hall(
                name="MARQUE ONE",
                capacity_guests=500,
                capacity_tables=50,
                day_price=150000.00,
                night_price=300000.00,
                is_active=True,
            )
        )
    db.commit()

    # settings defaults
    defaults = {
        "default_advance_percent": "50",
        "duty_start_time": "09:00",
        "late_grace_minutes": "15",
        "slot_day_start": "12:00",
        "slot_day_end": "16:00",
        "slot_night_start": "19:00",
        "slot_night_end": "23:00",
        "app_name": "MARQUE ONE",
    }
    for k, v in defaults.items():
        if not db.query(ApplicationSetting).filter(ApplicationSetting.key == k).first():
            db.add(ApplicationSetting(key=k, value=v, description="default"))
    db.commit()

    # first admin
    admin_phone = settings.FIRST_ADMIN_PHONE
    admin_user = None
    if not db.query(User).filter(User.phone == admin_phone).first():
        role = db.query(Role).filter(Role.name == "super_admin").first()
        admin_user = User(
            role_id=role.id,
            full_name=settings.FIRST_ADMIN_NAME,
            phone=admin_phone,
            password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
            is_active=True,
        )
        db.add(admin_user)
        db.flush()
    else:
        admin_user = db.query(User).filter(User.phone == admin_phone).first()

    # link employee record for admin
    if not db.query(Employee).filter(Employee.user_id == admin_user.id).first():
        db.add(
            Employee(
                user_id=admin_user.id,
                employee_code="EMP-0001",
                full_name=settings.FIRST_ADMIN_NAME,
                phone=admin_phone,
                role="manager",
                duty_start_time=time(9, 0),
                is_active=True,
            )
        )
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
        print("Seeded.")
    finally:
        db.close()
