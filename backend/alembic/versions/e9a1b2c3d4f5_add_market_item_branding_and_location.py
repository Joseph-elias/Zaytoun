"""add_market_item_branding_and_location

Revision ID: e9a1b2c3d4f5
Revises: d8b7c6a5e4f3
Create Date: 2026-04-07 16:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9a1b2c3d4f5"
down_revision: Union[str, None] = "d8b7c6a5e4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {col["name"] for col in inspector.get_columns("farmer_market_items")}

    if "brand_logo_url" not in columns:
        op.add_column("farmer_market_items", sa.Column("brand_logo_url", sa.String(length=500), nullable=True))
    if "photo_url" not in columns:
        op.add_column("farmer_market_items", sa.Column("photo_url", sa.String(length=500), nullable=True))
    if "pickup_location" not in columns:
        op.add_column("farmer_market_items", sa.Column("pickup_location", sa.String(length=180), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {col["name"] for col in inspector.get_columns("farmer_market_items")}

    if "pickup_location" in columns:
        op.drop_column("farmer_market_items", "pickup_location")
    if "photo_url" in columns:
        op.drop_column("farmer_market_items", "photo_url")
    if "brand_logo_url" in columns:
        op.drop_column("farmer_market_items", "brand_logo_url")
