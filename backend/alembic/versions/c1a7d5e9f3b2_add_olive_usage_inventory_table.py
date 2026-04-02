"""add_olive_usage_inventory_table

Revision ID: c1a7d5e9f3b2
Revises: b4f2c8d1e7a9
Create Date: 2026-04-03 00:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a7d5e9f3b2"
down_revision: Union[str, None] = "b4f2c8d1e7a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_olive_usages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("used_on", sa.Date(), nullable=True),
        sa.Column("tanks_used", sa.Numeric(12, 2), nullable=False),
        sa.Column("usage_type", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["farmer_olive_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farmer_olive_usages_farmer_user_id", "farmer_olive_usages", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_olive_usages_season_id", "farmer_olive_usages", ["season_id"], unique=False)
    op.create_index("ix_farmer_olive_usages_used_on", "farmer_olive_usages", ["used_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_farmer_olive_usages_used_on", table_name="farmer_olive_usages")
    op.drop_index("ix_farmer_olive_usages_season_id", table_name="farmer_olive_usages")
    op.drop_index("ix_farmer_olive_usages_farmer_user_id", table_name="farmer_olive_usages")
    op.drop_table("farmer_olive_usages")
