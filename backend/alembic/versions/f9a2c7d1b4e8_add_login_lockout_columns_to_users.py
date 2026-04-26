"""add_login_lockout_columns_to_users

Revision ID: f9a2c7d1b4e8
Revises: e4a1b7c9d2f3
Create Date: 2026-04-26 16:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9a2c7d1b4e8"
down_revision: Union[str, None] = "e4a1b7c9d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("users")
    with op.batch_alter_table("users") as batch_op:
        if "login_failed_attempts" not in columns:
            batch_op.add_column(sa.Column("login_failed_attempts", sa.Integer(), nullable=False, server_default="0"))
        if "login_locked_until" not in columns:
            batch_op.add_column(sa.Column("login_locked_until", sa.DateTime(), nullable=True))

    # Ensure server default is removed after initial backfill consistency.
    with op.batch_alter_table("users") as batch_op:
        if "login_failed_attempts" in _column_names("users"):
            batch_op.alter_column("login_failed_attempts", server_default=None)


def downgrade() -> None:
    columns = _column_names("users")
    with op.batch_alter_table("users") as batch_op:
        if "login_locked_until" in columns:
            batch_op.drop_column("login_locked_until")
        if "login_failed_attempts" in columns:
            batch_op.drop_column("login_failed_attempts")
