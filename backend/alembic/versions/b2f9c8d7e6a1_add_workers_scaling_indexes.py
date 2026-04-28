"""add_workers_scaling_indexes

Revision ID: b2f9c8d7e6a1
Revises: a4d8b7c6e5f1
Create Date: 2026-04-28 14:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2f9c8d7e6a1"
down_revision: Union[str, None] = "a4d8b7c6e5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    idx = _index_names("workers")
    if "ix_workers_phone" not in idx:
        op.create_index("ix_workers_phone", "workers", ["phone"])
    if "ix_workers_available_created_at" not in idx:
        op.create_index("ix_workers_available_created_at", "workers", ["available", "created_at"])


def downgrade() -> None:
    idx = _index_names("workers")
    if "ix_workers_available_created_at" in idx:
        op.drop_index("ix_workers_available_created_at", table_name="workers")
    if "ix_workers_phone" in idx:
        op.drop_index("ix_workers_phone", table_name="workers")
