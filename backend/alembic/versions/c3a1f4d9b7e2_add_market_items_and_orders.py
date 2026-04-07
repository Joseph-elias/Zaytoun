"""add_market_items_and_orders

Revision ID: c3a1f4d9b7e2
Revises: a6d4c2b1e9f8
Create Date: 2026-04-07 13:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3a1f4d9b7e2"
down_revision: Union[str, None] = "a6d4c2b1e9f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_market_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("item_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=True),
        sa.Column("unit_label", sa.String(length=50), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity_available", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farmer_market_items_farmer_user_id", "farmer_market_items", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_market_items_is_active", "farmer_market_items", ["is_active"], unique=False)
    op.create_index("ix_farmer_market_items_item_name", "farmer_market_items", ["item_name"], unique=False)

    op.create_table(
        "market_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("market_item_id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("customer_user_id", sa.Uuid(), nullable=False),
        sa.Column("item_name_snapshot", sa.String(length=120), nullable=False),
        sa.Column("unit_label_snapshot", sa.String(length=50), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity_ordered", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("note", sa.String(length=400), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_item_id"], ["farmer_market_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_orders_created_at", "market_orders", ["created_at"], unique=False)
    op.create_index("ix_market_orders_customer_user_id", "market_orders", ["customer_user_id"], unique=False)
    op.create_index("ix_market_orders_farmer_user_id", "market_orders", ["farmer_user_id"], unique=False)
    op.create_index("ix_market_orders_item_id", "market_orders", ["market_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_orders_item_id", table_name="market_orders")
    op.drop_index("ix_market_orders_farmer_user_id", table_name="market_orders")
    op.drop_index("ix_market_orders_customer_user_id", table_name="market_orders")
    op.drop_index("ix_market_orders_created_at", table_name="market_orders")
    op.drop_table("market_orders")

    op.drop_index("ix_farmer_market_items_item_name", table_name="farmer_market_items")
    op.drop_index("ix_farmer_market_items_is_active", table_name="farmer_market_items")
    op.drop_index("ix_farmer_market_items_farmer_user_id", table_name="farmer_market_items")
    op.drop_table("farmer_market_items")
