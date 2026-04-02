"""add_custom_item_fields_to_olive_sales

Revision ID: f2c9e4a1d7b5
Revises: e8d1a4f6b9c3
Create Date: 2026-04-03 04:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c9e4a1d7b5"
down_revision: Union[str, None] = "e8d1a4f6b9c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_olive_sales") as batch_op:
        batch_op.add_column(sa.Column("custom_item_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("custom_quantity_sold", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("custom_unit_label", sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column("custom_price_per_unit", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("farmer_olive_sales") as batch_op:
        batch_op.drop_column("custom_price_per_unit")
        batch_op.drop_column("custom_unit_label")
        batch_op.drop_column("custom_quantity_sold")
        batch_op.drop_column("custom_item_name")
