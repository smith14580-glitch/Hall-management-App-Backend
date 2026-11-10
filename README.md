# MARQUE ONE — Backend API

FastAPI + SQLAlchemy + Alembic backend for the MARQUE ONE Marriage Hall Management System.

## Stack

- FastAPI (Python 3.12)
- SQLAlchemy 2 + Alembic
- PostgreSQL (Neon)
- JWT auth + RBAC (super_admin / staff / waiter)

## Features

- Auth: login, refresh, me, change-password
- Bookings: create/list/get, availability check, conflict safeguard (409), confirm/cancel/complete transitions
- Payments: record, receipt, void, outstanding
- Tables + allocations (capacity rule)
- Customers, Employees, Attendance (check-in/out, late rule)
- Dashboard summary, Settings, Notifications, Reports + CSV export

## Setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# create .env from .env.example (fill DATABASE_URL, JWT_SECRET_KEY, FIRST_ADMIN_*)

# migrations
.venv\Scripts\python -m alembic upgrade head

# seed (roles, hall MARQUE ONE, settings, first admin)
.venv\Scripts\python seed.py

# run
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

## Env vars

See `.env.example` — names only, never commit real values.
