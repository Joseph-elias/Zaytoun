"""add_work_date_to_bookings

Revision ID: b1f3c2d4e5f6
Revises: 08509f1e5d3e
Create Date: 2026-04-01 22:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1f3c2d4e5f6"
down_revision: Union[str, None] = "08509f1e5d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(sa.Column("work_date", sa.Date(), nullable=True))
        batch_op.alter_column("day", existing_type=sa.String(length=10), nullable=True)

    op.create_index("ix_bookings_worker_id_work_date", "bookings", ["worker_id", "work_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_worker_id_work_date", table_name="bookings")

    with op.batch_alter_table("bookings") as batch_op:
        batch_op.alter_column("day", existing_type=sa.String(length=10), nullable=False)
        batch_op.drop_column("work_date")
