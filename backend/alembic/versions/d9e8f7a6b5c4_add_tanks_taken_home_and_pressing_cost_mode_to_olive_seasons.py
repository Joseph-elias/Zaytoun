"""add_tanks_taken_home_and_pressing_cost_mode_to_olive_seasons

Revision ID: d9e8f7a6b5c4
Revises: b6d9f2a1c3e4
Create Date: 2026-04-05 20:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9e8f7a6b5c4"
down_revision: Union[str, None] = "b6d9f2a1c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_olive_seasons") as batch_op:
        batch_op.add_column(sa.Column("tanks_taken_home_20l", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("pressing_cost_mode", sa.String(length=20), nullable=False, server_default="money"))
        batch_op.add_column(sa.Column("pressing_cost_oil_tanks_20l", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("farmer_olive_seasons") as batch_op:
        batch_op.drop_column("pressing_cost_oil_tanks_20l")
        batch_op.drop_column("pressing_cost_mode")
        batch_op.drop_column("tanks_taken_home_20l")
