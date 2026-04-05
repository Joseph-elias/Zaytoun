"""add_inventory_year_to_items

Revision ID: a6d4c2b1e9f8
Revises: f7b9c3d1e2a4
Create Date: 2026-04-06 00:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a6d4c2b1e9f8"
down_revision: Union[str, None] = "f7b9c3d1e2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_olive_inventory_items") as batch_op:
        batch_op.add_column(sa.Column("inventory_year", sa.Integer(), nullable=True))

    op.execute("UPDATE farmer_olive_inventory_items SET inventory_year = CAST(strftime('%Y', COALESCE(created_at, CURRENT_TIMESTAMP)) AS INTEGER) WHERE inventory_year IS NULL")

    with op.batch_alter_table("farmer_olive_inventory_items") as batch_op:
        batch_op.alter_column("inventory_year", existing_type=sa.Integer(), nullable=False)

    op.create_index("ix_farmer_olive_inventory_items_year", "farmer_olive_inventory_items", ["inventory_year"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_farmer_olive_inventory_items_year", table_name="farmer_olive_inventory_items")

    with op.batch_alter_table("farmer_olive_inventory_items") as batch_op:
        batch_op.drop_column("inventory_year")
