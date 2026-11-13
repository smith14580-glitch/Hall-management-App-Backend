from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    bookings,
    availability,
    payments,
    tables,
    customers,
    employees,
    attendance,
    dashboard,
    halls,
    notifications,
    reports,
    salary,
    quotations,
)

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
api_router.include_router(halls.router)
api_router.include_router(halls.router_pricing)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(reports.router_audit)
api_router.include_router(salary.router)
api_router.include_router(quotations.router)
