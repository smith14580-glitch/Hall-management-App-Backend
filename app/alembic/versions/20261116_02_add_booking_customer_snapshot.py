"""add booking customer name/phone snapshot

Revision ID: 20261116_02
Revises: 20261116_01
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20261116_02"
down_revision = "20261116_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("customer_name", sa.String(120), nullable=True))
    op.add_column("bookings", sa.Column("customer_phone", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "customer_phone")
    op.drop_column("bookings", "customer_name")
