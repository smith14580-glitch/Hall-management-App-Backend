"""add booking add-ons and guest pricing

Revision ID: 20261116_01
Revises: 20261115_01
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20261116_01"
down_revision = "20261115_01"
branch_labels = None
depends_on = None


ADDON_COLUMNS = [
    sa.Column("refreshment_type", sa.String(20), nullable=False, server_default="none"),
    sa.Column("refreshment_custom_name", sa.String(100), nullable=True),
    sa.Column("refreshment_guests", sa.Integer(), nullable=True),
    sa.Column("refreshment_rate", sa.Numeric(12, 2), nullable=True),
    sa.Column("refreshment_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    sa.Column("hall_type", sa.String(10), nullable=False, server_default="ac"),
    sa.Column("hall_type_rate", sa.Numeric(12, 2), nullable=True),
    sa.Column("hall_type_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    sa.Column("guest_rate", sa.Numeric(12, 2), nullable=False, server_default="0"),
    sa.Column("guest_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
]

NEW_SETTINGS = [
    ("addon_refreshment_water_per_guest", "100"),
    ("addon_refreshment_juice_per_guest", "300"),
    ("addon_refreshment_both_per_guest", "350"),
    ("addon_ac_price", "20000"),
    ("addon_non_ac_price", "0"),
    ("guest_price_per_guest", "0"),
]


def upgrade() -> None:
    for column in ADDON_COLUMNS:
        op.add_column("bookings", column)

    op.create_check_constraint(
        "ck_bookings_refreshment_type",
        "bookings",
        "refreshment_type IN ('none','water','juice','both','custom')",
    )
    op.create_check_constraint(
        "ck_bookings_hall_type",
        "bookings",
        "hall_type IN ('ac','non_ac')",
    )

    # v1 single refreshment rate is superseded by per-option rates.
    op.execute("DELETE FROM application_settings WHERE key = 'addon_refreshment_per_guest'")

    values_sql = ", ".join(f"('{k}', '{v}')" for k, v in NEW_SETTINGS)
    op.execute(
        f"""
        INSERT INTO application_settings (id, key, value, description)
        SELECT gen_random_uuid(), v.key, v.value, 'default'
        FROM (VALUES {values_sql}) AS v(key, value)
        WHERE NOT EXISTS (
            SELECT 1 FROM application_settings s WHERE s.key = v.key
        )
        """
    )


def downgrade() -> None:
    keys_sql = ", ".join(f"'{k}'" for k, _ in NEW_SETTINGS)
    op.execute(f"DELETE FROM application_settings WHERE key IN ({keys_sql})")
    op.execute(
        """
        INSERT INTO application_settings (id, key, value, description)
        SELECT gen_random_uuid(), 'addon_refreshment_per_guest', '500', 'default'
        WHERE NOT EXISTS (
            SELECT 1 FROM application_settings WHERE key = 'addon_refreshment_per_guest'
        )
        """
    )

    op.drop_constraint("ck_bookings_hall_type", "bookings", type_="check")
    op.drop_constraint("ck_bookings_refreshment_type", "bookings", type_="check")
    for column in reversed(ADDON_COLUMNS):
        op.drop_column("bookings", column.name)
