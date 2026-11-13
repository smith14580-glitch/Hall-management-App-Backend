"""add quotation tables

Revision ID: 20261112_01
Revises:
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261112_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotation_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_body", sa.Text(), nullable=False),
        sa.Column("facilities", sa.Text(), nullable=True),
        sa.Column("chargeable_items", sa.Text(), nullable=True),
        sa.Column("policies", sa.Text(), nullable=True),
        sa.Column("office_timings", sa.String(200), nullable=True),
        sa.Column("manager_name", sa.String(120), nullable=True),
        sa.Column("manager_phone", sa.String(20), nullable=True),
        sa.Column("location_link", sa.String(500), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enquiry_no", sa.String(30), nullable=False, unique=True),
        sa.Column("client_name", sa.String(120), nullable=False),
        sa.Column("client_phone", sa.String(20), nullable=False),
        sa.Column("source", sa.String(30), nullable=True),
        sa.Column("event_type", sa.String(60), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("slot", sa.String(10), nullable=True),
        sa.Column("guest_count", sa.Integer(), nullable=True),
        sa.Column("hall_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("halls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("package_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("advance_percent", sa.Integer(), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_quotations_enquiry_no", "quotations", ["enquiry_no"])
    op.create_index("ix_quotations_client_phone", "quotations", ["client_phone"])


def downgrade() -> None:
    op.drop_index("ix_quotations_client_phone", table_name="quotations")
    op.drop_index("ix_quotations_enquiry_no", table_name="quotations")
    op.drop_table("quotations")
    op.drop_table("quotation_settings")
