"""add_season_id_to_bookings

Revision ID: e1b2c3d4f5a6
Revises: d9e8f7a6b5c4
Create Date: 2026-04-05 22:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1b2c3d4f5a6"
down_revision: Union[str, None] = "d9e8f7a6b5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(sa.Column("season_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_bookings_season_id_farmer_olive_seasons",
            "farmer_olive_seasons",
            ["season_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index("ix_bookings_season_id", "bookings", ["season_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_season_id", table_name="bookings")

    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_constraint("fk_bookings_season_id_farmer_olive_seasons", type_="foreignkey")
        batch_op.drop_column("season_id")
