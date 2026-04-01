"""add_available_dates_to_workers

Revision ID: c7a9d3e1f2b4
Revises: b1f3c2d4e5f6
Create Date: 2026-04-01 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7a9d3e1f2b4"
down_revision: Union[str, None] = "b1f3c2d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workers") as batch_op:
        batch_op.add_column(sa.Column("available_dates", sa.String(length=4000), nullable=False, server_default=","))


def downgrade() -> None:
    with op.batch_alter_table("workers") as batch_op:
        batch_op.drop_column("available_dates")
