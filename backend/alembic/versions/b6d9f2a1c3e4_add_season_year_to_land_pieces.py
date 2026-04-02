"""add_season_year_to_land_pieces

Revision ID: b6d9f2a1c3e4
Revises: a2c4e6f8b1d9
Create Date: 2026-04-03 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6d9f2a1c3e4"
down_revision: Union[str, None] = "a2c4e6f8b1d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_olive_land_pieces") as batch_op:
        batch_op.add_column(sa.Column("season_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("farmer_olive_land_pieces") as batch_op:
        batch_op.drop_column("season_year")
