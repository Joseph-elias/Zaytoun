"""add_market_order_validation_and_chat

Revision ID: d8b7c6a5e4f3
Revises: c3a1f4d9b7e2
Create Date: 2026-04-07 15:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8b7c6a5e4f3"
down_revision: Union[str, None] = "c3a1f4d9b7e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    order_columns = {col["name"] for col in inspector.get_columns("market_orders")}

    if "pickup_at" not in order_columns:
        op.add_column("market_orders", sa.Column("pickup_at", sa.DateTime(), nullable=True))
    if "farmer_response_note" not in order_columns:
        op.add_column("market_orders", sa.Column("farmer_response_note", sa.String(length=400), nullable=True))
    if "updated_at" not in order_columns:
        op.add_column("market_orders", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.execute(sa.text("UPDATE market_orders SET updated_at = created_at WHERE updated_at IS NULL"))

    table_names = set(inspector.get_table_names())
    if "market_order_messages" not in table_names:
        op.create_table(
            "market_order_messages",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("market_order_id", sa.Uuid(), nullable=False),
            sa.Column("sender_user_id", sa.Uuid(), nullable=False),
            sa.Column("content", sa.String(length=1200), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["market_order_id"], ["market_orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_market_order_messages_order_id", "market_order_messages", ["market_order_id"], unique=False)
        op.create_index("ix_market_order_messages_created_at", "market_order_messages", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = set(inspector.get_table_names())
    if "market_order_messages" in table_names:
        index_names = {idx["name"] for idx in inspector.get_indexes("market_order_messages")}
        if "ix_market_order_messages_created_at" in index_names:
            op.drop_index("ix_market_order_messages_created_at", table_name="market_order_messages")
        if "ix_market_order_messages_order_id" in index_names:
            op.drop_index("ix_market_order_messages_order_id", table_name="market_order_messages")
        op.drop_table("market_order_messages")

    order_columns = {col["name"] for col in inspector.get_columns("market_orders")}
    if "updated_at" in order_columns:
        op.drop_column("market_orders", "updated_at")
    if "farmer_response_note" in order_columns:
        op.drop_column("market_orders", "farmer_response_note")
    if "pickup_at" in order_columns:
        op.drop_column("market_orders", "pickup_at")
