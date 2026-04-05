"""add_oil_tank_unit_price_to_olive_seasons

Revision ID: f7b9c3d1e2a4
Revises: e1b2c3d4f5a6
Create Date: 2026-04-05 23:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7b9c3d1e2a4"
down_revision: Union[str, None] = "e1b2c3d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_olive_seasons") as batch_op:
        batch_op.add_column(sa.Column("pressing_cost_oil_tank_unit_price", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("farmer_olive_seasons") as batch_op:
        batch_op.drop_column("pressing_cost_oil_tank_unit_price")
