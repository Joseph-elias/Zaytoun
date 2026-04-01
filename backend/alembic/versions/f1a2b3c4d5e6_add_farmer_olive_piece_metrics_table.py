"""add_farmer_olive_piece_metrics_table

Revision ID: f1a2b3c4d5e6
Revises: e2f7a9b4c1d0
Create Date: 2026-04-02 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e2f7a9b4c1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_olive_piece_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("piece_label", sa.String(length=120), nullable=False),
        sa.Column("harvested_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("tanks_20l", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_user_id", "season_year", "piece_label", name="uq_farmer_piece_year_label"),
    )
    op.create_index("ix_farmer_piece_metrics_farmer_user_id", "farmer_olive_piece_metrics", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_piece_metrics_season_year", "farmer_olive_piece_metrics", ["season_year"], unique=False)
    op.create_index("ix_farmer_piece_metrics_piece_label", "farmer_olive_piece_metrics", ["piece_label"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_farmer_piece_metrics_piece_label", table_name="farmer_olive_piece_metrics")
    op.drop_index("ix_farmer_piece_metrics_season_year", table_name="farmer_olive_piece_metrics")
    op.drop_index("ix_farmer_piece_metrics_farmer_user_id", table_name="farmer_olive_piece_metrics")
    op.drop_table("farmer_olive_piece_metrics")
