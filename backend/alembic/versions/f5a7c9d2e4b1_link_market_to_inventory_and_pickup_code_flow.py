"""link_market_to_inventory_and_pickup_code_flow

Revision ID: f5a7c9d2e4b1
Revises: c4d5e6f7a8b9
Create Date: 2026-04-07 22:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a7c9d2e4b1"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _foreign_key_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}


def upgrade() -> None:
    inventory_columns = _column_names("farmer_olive_inventory_items")
    if "quantity_pending" not in inventory_columns:
        with op.batch_alter_table("farmer_olive_inventory_items") as batch_op:
            batch_op.add_column(sa.Column("quantity_pending", sa.Numeric(12, 2), nullable=False, server_default="0"))
        op.execute(sa.text("UPDATE farmer_olive_inventory_items SET quantity_pending = 0 WHERE quantity_pending IS NULL"))

    item_columns = _column_names("farmer_market_items")
    item_fks = _foreign_key_names("farmer_market_items")
    with op.batch_alter_table("farmer_market_items") as batch_op:
        if "linked_inventory_item_id" not in item_columns:
            batch_op.add_column(sa.Column("linked_inventory_item_id", sa.Uuid(), nullable=True))
        if "fk_farmer_market_items_linked_inventory_item_id" not in item_fks:
            batch_op.create_foreign_key(
                "fk_farmer_market_items_linked_inventory_item_id",
                "farmer_olive_inventory_items",
                ["linked_inventory_item_id"],
                ["id"],
                ondelete="SET NULL",
            )

    order_columns = _column_names("market_orders")
    order_fks = _foreign_key_names("market_orders")
    with op.batch_alter_table("market_orders") as batch_op:
        if "linked_inventory_item_id" not in order_columns:
            batch_op.add_column(sa.Column("linked_inventory_item_id", sa.Uuid(), nullable=True))
        if "inventory_reserved_quantity" not in order_columns:
            batch_op.add_column(sa.Column("inventory_reserved_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"))
        if "inventory_shortage_alert" not in order_columns:
            batch_op.add_column(sa.Column("inventory_shortage_alert", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "inventory_shortage_note" not in order_columns:
            batch_op.add_column(sa.Column("inventory_shortage_note", sa.String(length=400), nullable=True))
        if "pickup_code" not in order_columns:
            batch_op.add_column(sa.Column("pickup_code", sa.String(length=12), nullable=True))
        if "picked_up_at" not in order_columns:
            batch_op.add_column(sa.Column("picked_up_at", sa.DateTime(), nullable=True))
        if "fk_market_orders_linked_inventory_item_id" not in order_fks:
            batch_op.create_foreign_key(
                "fk_market_orders_linked_inventory_item_id",
                "farmer_olive_inventory_items",
                ["linked_inventory_item_id"],
                ["id"],
                ondelete="SET NULL",
            )

    op.execute(sa.text("UPDATE market_orders SET inventory_reserved_quantity = 0 WHERE inventory_reserved_quantity IS NULL"))
    op.execute(sa.text("UPDATE market_orders SET inventory_shortage_alert = 0 WHERE inventory_shortage_alert IS NULL"))


def downgrade() -> None:
    order_columns = _column_names("market_orders")
    order_fks = _foreign_key_names("market_orders")
    with op.batch_alter_table("market_orders") as batch_op:
        if "fk_market_orders_linked_inventory_item_id" in order_fks:
            batch_op.drop_constraint("fk_market_orders_linked_inventory_item_id", type_="foreignkey")
        if "picked_up_at" in order_columns:
            batch_op.drop_column("picked_up_at")
        if "pickup_code" in order_columns:
            batch_op.drop_column("pickup_code")
        if "inventory_shortage_note" in order_columns:
            batch_op.drop_column("inventory_shortage_note")
        if "inventory_shortage_alert" in order_columns:
            batch_op.drop_column("inventory_shortage_alert")
        if "inventory_reserved_quantity" in order_columns:
            batch_op.drop_column("inventory_reserved_quantity")
        if "linked_inventory_item_id" in order_columns:
            batch_op.drop_column("linked_inventory_item_id")

    item_columns = _column_names("farmer_market_items")
    item_fks = _foreign_key_names("farmer_market_items")
    with op.batch_alter_table("farmer_market_items") as batch_op:
        if "fk_farmer_market_items_linked_inventory_item_id" in item_fks:
            batch_op.drop_constraint("fk_farmer_market_items_linked_inventory_item_id", type_="foreignkey")
        if "linked_inventory_item_id" in item_columns:
            batch_op.drop_column("linked_inventory_item_id")

    inventory_columns = _column_names("farmer_olive_inventory_items")
    if "quantity_pending" in inventory_columns:
        with op.batch_alter_table("farmer_olive_inventory_items") as batch_op:
            batch_op.drop_column("quantity_pending")
