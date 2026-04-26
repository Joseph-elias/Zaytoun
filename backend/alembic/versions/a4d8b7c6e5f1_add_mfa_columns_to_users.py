"""add_mfa_columns_to_users

Revision ID: a4d8b7c6e5f1
Revises: f9a2c7d1b4e8
Create Date: 2026-04-26 18:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4d8b7c6e5f1"
down_revision: Union[str, None] = "f9a2c7d1b4e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("users")
    with op.batch_alter_table("users") as batch_op:
        if "mfa_enabled" not in columns:
            batch_op.add_column(sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        if "mfa_enabled_at" not in columns:
            batch_op.add_column(sa.Column("mfa_enabled_at", sa.DateTime(), nullable=True))
        if "mfa_totp_secret" not in columns:
            batch_op.add_column(sa.Column("mfa_totp_secret", sa.String(length=128), nullable=True))
        if "mfa_totp_pending_secret" not in columns:
            batch_op.add_column(sa.Column("mfa_totp_pending_secret", sa.String(length=128), nullable=True))

    with op.batch_alter_table("users") as batch_op:
        if "mfa_enabled" in _column_names("users"):
            batch_op.alter_column("mfa_enabled", server_default=None)


def downgrade() -> None:
    columns = _column_names("users")
    with op.batch_alter_table("users") as batch_op:
        if "mfa_totp_pending_secret" in columns:
            batch_op.drop_column("mfa_totp_pending_secret")
        if "mfa_totp_secret" in columns:
            batch_op.drop_column("mfa_totp_secret")
        if "mfa_enabled_at" in columns:
            batch_op.drop_column("mfa_enabled_at")
        if "mfa_enabled" in columns:
            batch_op.drop_column("mfa_enabled")
