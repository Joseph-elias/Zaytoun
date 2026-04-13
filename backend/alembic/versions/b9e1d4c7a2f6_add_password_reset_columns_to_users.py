"""add_password_reset_columns_to_users

Revision ID: b9e1d4c7a2f6
Revises: a8d2c4e6f9b1
Create Date: 2026-04-13 20:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9e1d4c7a2f6"
down_revision: Union[str, None] = "a8d2c4e6f9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "password_reset_code_hash" not in columns:
            batch_op.add_column(sa.Column("password_reset_code_hash", sa.String(length=255), nullable=True))
        if "password_reset_expires_at" not in columns:
            batch_op.add_column(sa.Column("password_reset_expires_at", sa.DateTime(), nullable=True))
        if "password_reset_requested_at" not in columns:
            batch_op.add_column(sa.Column("password_reset_requested_at", sa.DateTime(), nullable=True))
        if "password_reset_attempts" not in columns:
            batch_op.add_column(
                sa.Column("password_reset_attempts", sa.Integer(), nullable=False, server_default="0")
            )

    op.execute(sa.text("UPDATE users SET password_reset_attempts = 0 WHERE password_reset_attempts IS NULL"))


def downgrade() -> None:
    columns = _column_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "password_reset_attempts" in columns:
            batch_op.drop_column("password_reset_attempts")
        if "password_reset_requested_at" in columns:
            batch_op.drop_column("password_reset_requested_at")
        if "password_reset_expires_at" in columns:
            batch_op.drop_column("password_reset_expires_at")
        if "password_reset_code_hash" in columns:
            batch_op.drop_column("password_reset_code_hash")
