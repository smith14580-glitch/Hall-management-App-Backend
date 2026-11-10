from fastapi import APIRouter

from app.api.v1.endpoints import auth, bookings, availability, payments, tables, customers, employees, attendance, dashboard, notifications, reports

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(bookings.router)
api_router.include_router(availability.router)
api_router.include_router(payments.router)
api_router.include_router(tables.router)
api_router.include_router(customers.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(dashboard.router)
api_router.include_router(dashboard.router_settings)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
