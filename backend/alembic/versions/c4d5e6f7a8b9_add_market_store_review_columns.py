"""add_market_store_review_columns

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-07 21:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("market_orders")}

    if "market_rating" not in columns:
        op.add_column("market_orders", sa.Column("market_rating", sa.Integer(), nullable=True))
    if "market_review" not in columns:
        op.add_column("market_orders", sa.Column("market_review", sa.String(length=800), nullable=True))
    if "market_reviewed_at" not in columns:
        op.add_column("market_orders", sa.Column("market_reviewed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("market_orders")}

    if "market_reviewed_at" in columns:
        op.drop_column("market_orders", "market_reviewed_at")
    if "market_review" in columns:
        op.drop_column("market_orders", "market_review")
    if "market_rating" in columns:
        op.drop_column("market_orders", "market_rating")
