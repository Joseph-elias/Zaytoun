"""add_token_version_to_users_for_session_revocation

Revision ID: d1a7c9e4b2f5
Revises: c2f4a8d9e1b3
Create Date: 2026-04-13 22:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1a7c9e4b2f5"
down_revision: Union[str, None] = "c2f4a8d9e1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "token_version" not in columns:
            batch_op.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))

    op.execute(sa.text("UPDATE users SET token_version = 0 WHERE token_version IS NULL"))


def downgrade() -> None:
    columns = _column_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "token_version" in columns:
            batch_op.drop_column("token_version")
