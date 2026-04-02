"""allow_multiple_seasons_per_year_by_land_piece

Revision ID: a9c1d8e4b7f0
Revises: f2c3d4e5f6a7
Create Date: 2026-04-02 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9c1d8e4b7f0"
down_revision: Union[str, None] = "f2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE farmer_olive_seasons
        SET land_piece_name = 'Unnamed'
        WHERE land_piece_name IS NULL OR TRIM(land_piece_name) = ''
        """
    )

    with op.batch_alter_table("farmer_olive_seasons") as batch_op:
        batch_op.drop_constraint("uq_farmer_olive_seasons_farmer_year", type_="unique")
        batch_op.alter_column("land_piece_name", existing_type=sa.String(length=120), nullable=False)
        batch_op.create_unique_constraint(
            "uq_farmer_olive_seasons_farmer_year_piece",
            ["farmer_user_id", "season_year", "land_piece_name"],
        )


def downgrade() -> None:
    with op.batch_alter_table("farmer_olive_seasons") as batch_op:
        batch_op.drop_constraint("uq_farmer_olive_seasons_farmer_year_piece", type_="unique")
        batch_op.alter_column("land_piece_name", existing_type=sa.String(length=120), nullable=True)
        batch_op.create_unique_constraint("uq_farmer_olive_seasons_farmer_year", ["farmer_user_id", "season_year"])
