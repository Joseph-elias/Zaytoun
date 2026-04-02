"""add_inventory_items_and_sale_link

Revision ID: d4e7c2b9a1f3
Revises: f2c9e4a1d7b5
Create Date: 2026-04-03 05:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e7c2b9a1f3"
down_revision: Union[str, None] = "f2c9e4a1d7b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_olive_inventory_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("item_name", sa.String(length=120), nullable=False),
        sa.Column("unit_label", sa.String(length=60), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(12, 2), nullable=False),
        sa.Column("default_price_per_unit", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farmer_olive_inventory_items_farmer_user_id", "farmer_olive_inventory_items", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_olive_inventory_items_name", "farmer_olive_inventory_items", ["item_name"], unique=False)

    with op.batch_alter_table("farmer_olive_sales") as batch_op:
        batch_op.add_column(sa.Column("custom_inventory_item_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_farmer_olive_sales_custom_inventory_item_id",
            "farmer_olive_inventory_items",
            ["custom_inventory_item_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("farmer_olive_sales") as batch_op:
        batch_op.drop_constraint("fk_farmer_olive_sales_custom_inventory_item_id", type_="foreignkey")
        batch_op.drop_column("custom_inventory_item_id")

    op.drop_index("ix_farmer_olive_inventory_items_name", table_name="farmer_olive_inventory_items")
    op.drop_index("ix_farmer_olive_inventory_items_farmer_user_id", table_name="farmer_olive_inventory_items")
    op.drop_table("farmer_olive_inventory_items")
