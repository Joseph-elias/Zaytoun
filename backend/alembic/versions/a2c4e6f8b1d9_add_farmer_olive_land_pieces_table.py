"""add_farmer_olive_land_pieces_table

Revision ID: a2c4e6f8b1d9
Revises: d4e7c2b9a1f3
Create Date: 2026-04-04 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2c4e6f8b1d9"
down_revision: Union[str, None] = "d4e7c2b9a1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_olive_land_pieces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("piece_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farmer_olive_land_pieces_farmer_user_id", "farmer_olive_land_pieces", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_olive_land_pieces_name", "farmer_olive_land_pieces", ["piece_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_farmer_olive_land_pieces_name", table_name="farmer_olive_land_pieces")
    op.drop_index("ix_farmer_olive_land_pieces_farmer_user_id", table_name="farmer_olive_land_pieces")
    op.drop_table("farmer_olive_land_pieces")
