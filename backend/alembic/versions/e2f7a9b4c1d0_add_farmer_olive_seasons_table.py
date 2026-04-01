"""add_farmer_olive_seasons_table

Revision ID: e2f7a9b4c1d0
Revises: d4b8a1c9e2f0
Create Date: 2026-04-02 01:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f7a9b4c1d0"
down_revision: Union[str, None] = "d4b8a1c9e2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_olive_seasons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("land_pieces", sa.Integer(), nullable=False),
        sa.Column("estimated_chonbol", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_chonbol", sa.Numeric(12, 2), nullable=True),
        sa.Column("kg_per_land_piece", sa.Numeric(12, 2), nullable=True),
        sa.Column("tanks_20l", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_user_id", "season_year", name="uq_farmer_olive_seasons_farmer_year"),
    )
    op.create_index("ix_farmer_olive_seasons_farmer_user_id", "farmer_olive_seasons", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_olive_seasons_season_year", "farmer_olive_seasons", ["season_year"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_farmer_olive_seasons_season_year", table_name="farmer_olive_seasons")
    op.drop_index("ix_farmer_olive_seasons_farmer_user_id", table_name="farmer_olive_seasons")
    op.drop_table("farmer_olive_seasons")
