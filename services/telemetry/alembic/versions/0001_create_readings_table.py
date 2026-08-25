"""create readings table

Revision ID: 0001
Revises:
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("power_kw", sa.Float(), nullable=False),
        sa.Column("voltage_v", sa.Float(), nullable=False),
    )
    op.create_index("ix_readings_device_id", "readings", ["device_id"])
    op.create_index("ix_readings_timestamp", "readings", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_readings_timestamp", table_name="readings")
    op.drop_index("ix_readings_device_id", table_name="readings")
    op.drop_table("readings")
