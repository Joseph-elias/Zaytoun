"""add_land_piece_name_to_olive_seasons

Revision ID: f2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-02 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c3d4e5f6a7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("farmer_olive_seasons", sa.Column("land_piece_name", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("farmer_olive_seasons", "land_piece_name")
