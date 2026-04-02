"""expand_olive_sales_to_multi_product_types

Revision ID: e8d1a4f6b9c3
Revises: c1a7d5e9f3b2
Create Date: 2026-04-03 03:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8d1a4f6b9c3"
down_revision: Union[str, None] = "c1a7d5e9f3b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_olive_sales") as batch_op:
        batch_op.add_column(sa.Column("sale_type", sa.String(length=30), nullable=False, server_default="oil_tank"))
        batch_op.add_column(sa.Column("raw_kg_sold", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("price_per_kg", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("containers_sold", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("container_size_label", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("kg_per_container", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("price_per_container", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("inventory_tanks_delta", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("total_revenue", sa.Numeric(12, 2), nullable=False, server_default="0"))

        batch_op.alter_column("tanks_sold", existing_type=sa.Numeric(12, 2), nullable=True)
        batch_op.alter_column("price_per_tank", existing_type=sa.Numeric(12, 2), nullable=True)

    op.execute(
        """
        UPDATE farmer_olive_sales
        SET
            sale_type = 'oil_tank',
            inventory_tanks_delta = COALESCE(tanks_sold, 0),
            total_revenue = COALESCE(tanks_sold, 0) * COALESCE(price_per_tank, 0)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE farmer_olive_sales
        SET
            tanks_sold = COALESCE(tanks_sold, 0),
            price_per_tank = COALESCE(price_per_tank, 0)
        """
    )

    with op.batch_alter_table("farmer_olive_sales") as batch_op:
        batch_op.alter_column("price_per_tank", existing_type=sa.Numeric(12, 2), nullable=False)
        batch_op.alter_column("tanks_sold", existing_type=sa.Numeric(12, 2), nullable=False)

        batch_op.drop_column("total_revenue")
        batch_op.drop_column("inventory_tanks_delta")
        batch_op.drop_column("price_per_container")
        batch_op.drop_column("kg_per_container")
        batch_op.drop_column("container_size_label")
        batch_op.drop_column("containers_sold")
        batch_op.drop_column("price_per_kg")
        batch_op.drop_column("raw_kg_sold")
        batch_op.drop_column("sale_type")
