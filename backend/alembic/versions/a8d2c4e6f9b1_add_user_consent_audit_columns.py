"""add_user_consent_audit_columns

Revision ID: a8d2c4e6f9b1
Revises: f5a7c9d2e4b1
Create Date: 2026-04-13 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8d2c4e6f9b1"
down_revision: Union[str, None] = "f5a7c9d2e4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "terms_accepted_at" not in columns:
            batch_op.add_column(sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
        if "data_consent_accepted_at" not in columns:
            batch_op.add_column(sa.Column("data_consent_accepted_at", sa.DateTime(), nullable=True))
        if "consent_version" not in columns:
            batch_op.add_column(sa.Column("consent_version", sa.String(length=32), nullable=True))

    op.execute(sa.text("UPDATE users SET terms_accepted_at = CURRENT_TIMESTAMP WHERE terms_accepted_at IS NULL"))
    op.execute(sa.text("UPDATE users SET data_consent_accepted_at = CURRENT_TIMESTAMP WHERE data_consent_accepted_at IS NULL"))
    op.execute(sa.text("UPDATE users SET consent_version = '2026-04-13' WHERE consent_version IS NULL"))


def downgrade() -> None:
    columns = _column_names("users")

    with op.batch_alter_table("users") as batch_op:
        if "consent_version" in columns:
            batch_op.drop_column("consent_version")
        if "data_consent_accepted_at" in columns:
            batch_op.drop_column("data_consent_accepted_at")
        if "terms_accepted_at" in columns:
            batch_op.drop_column("terms_accepted_at")
