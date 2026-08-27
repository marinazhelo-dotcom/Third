"""create users, alert_rules, alerts tables

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alert_rules_device_id", "alert_rules", ["device_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("power_kw", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_by", sa.String(), nullable=True),
    )
    op.create_index("ix_alerts_device_id", "alerts", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_device_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_alert_rules_device_id", table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
