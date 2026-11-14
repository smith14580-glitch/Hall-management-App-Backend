"""add booking confirmed_at

Revision ID: 20261114_01
Revises: 20261113_01
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20261114_01"
down_revision = "20261113_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "confirmed_at")
