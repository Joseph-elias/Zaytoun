"""add_email_to_users_for_auth_recovery

Revision ID: c2f4a8d9e1b3
Revises: b9e1d4c7a2f6
Create Date: 2026-04-13 21:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f4a8d9e1b3"
down_revision: Union[str, None] = "b9e1d4c7a2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    columns = _column_names("users")
    indexes = _index_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "email" not in columns:
            batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        if "ix_users_email" not in indexes:
            batch_op.create_index("ix_users_email", ["email"], unique=True)


def downgrade() -> None:
    columns = _column_names("users")
    indexes = _index_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "ix_users_email" in indexes:
            batch_op.drop_index("ix_users_email")
        if "email" in columns:
            batch_op.drop_column("email")
