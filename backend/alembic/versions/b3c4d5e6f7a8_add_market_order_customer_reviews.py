"""add_market_order_customer_reviews

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-07 20:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("market_orders")}

    if "customer_rating" not in columns:
        op.add_column("market_orders", sa.Column("customer_rating", sa.Integer(), nullable=True))
    if "customer_review" not in columns:
        op.add_column("market_orders", sa.Column("customer_review", sa.String(length=800), nullable=True))
    if "customer_reviewed_at" not in columns:
        op.add_column("market_orders", sa.Column("customer_reviewed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("market_orders")}

    if "customer_reviewed_at" in columns:
        op.drop_column("market_orders", "customer_reviewed_at")
    if "customer_review" in columns:
        op.drop_column("market_orders", "customer_review")
    if "customer_rating" in columns:
        op.drop_column("market_orders", "customer_rating")
