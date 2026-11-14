"""add advance payment method

Revision ID: 20261113_01
Revises: 20261112_01
Create Date: 2026-11-13
"""

from alembic import op

revision = "20261113_01"
down_revision = "20261112_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_payments_method", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_method",
        "payments",
        "method IN ('cash','bank_transfer','jazzcash','easypaisa','cheque','other','advance')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payments_method", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_method",
        "payments",
        "method IN ('cash','bank_transfer','jazzcash','easypaisa','cheque','other')",
    )
