"""add_farmer_store_profile_fields

Revision ID: a1b2c3d4e5f7
Revises: f0b1c2d3e4f6
Create Date: 2026-04-07 19:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f0b1c2d3e4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "store_name" not in columns:
        op.add_column("users", sa.Column("store_name", sa.String(length=120), nullable=True))
    if "store_banner_url" not in columns:
        op.add_column("users", sa.Column("store_banner_url", sa.String(length=500), nullable=True))
    if "store_about" not in columns:
        op.add_column("users", sa.Column("store_about", sa.String(length=600), nullable=True))
    if "store_opening_hours" not in columns:
        op.add_column("users", sa.Column("store_opening_hours", sa.String(length=180), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    if "store_opening_hours" in columns:
        op.drop_column("users", "store_opening_hours")
    if "store_about" in columns:
        op.drop_column("users", "store_about")
    if "store_banner_url" in columns:
        op.drop_column("users", "store_banner_url")
    if "store_name" in columns:
        op.drop_column("users", "store_name")
