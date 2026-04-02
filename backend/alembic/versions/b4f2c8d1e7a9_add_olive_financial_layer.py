"""add_olive_financial_layer

Revision ID: b4f2c8d1e7a9
Revises: a9c1d8e4b7f0
Create Date: 2026-04-02 23:58:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4f2c8d1e7a9"
down_revision: Union[str, None] = "a9c1d8e4b7f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("farmer_olive_seasons", sa.Column("pressing_cost", sa.Numeric(12, 2), nullable=True))

    op.create_table(
        "farmer_olive_labor_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("men_count", sa.Integer(), nullable=False),
        sa.Column("women_count", sa.Integer(), nullable=False),
        sa.Column("men_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("women_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["farmer_olive_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_user_id", "season_id", "work_date", name="uq_farmer_labor_day_once"),
    )
    op.create_index("ix_farmer_labor_days_farmer_user_id", "farmer_olive_labor_days", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_labor_days_season_id", "farmer_olive_labor_days", ["season_id"], unique=False)
    op.create_index("ix_farmer_labor_days_work_date", "farmer_olive_labor_days", ["work_date"], unique=False)

    op.create_table(
        "farmer_olive_sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("sold_on", sa.Date(), nullable=True),
        sa.Column("tanks_sold", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_per_tank", sa.Numeric(12, 2), nullable=False),
        sa.Column("buyer", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["farmer_olive_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farmer_olive_sales_farmer_user_id", "farmer_olive_sales", ["farmer_user_id"], unique=False)
    op.create_index("ix_farmer_olive_sales_season_id", "farmer_olive_sales", ["season_id"], unique=False)
    op.create_index("ix_farmer_olive_sales_sold_on", "farmer_olive_sales", ["sold_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_farmer_olive_sales_sold_on", table_name="farmer_olive_sales")
    op.drop_index("ix_farmer_olive_sales_season_id", table_name="farmer_olive_sales")
    op.drop_index("ix_farmer_olive_sales_farmer_user_id", table_name="farmer_olive_sales")
    op.drop_table("farmer_olive_sales")

    op.drop_index("ix_farmer_labor_days_work_date", table_name="farmer_olive_labor_days")
    op.drop_index("ix_farmer_labor_days_season_id", table_name="farmer_olive_labor_days")
    op.drop_index("ix_farmer_labor_days_farmer_user_id", table_name="farmer_olive_labor_days")
    op.drop_table("farmer_olive_labor_days")

    op.drop_column("farmer_olive_seasons", "pressing_cost")
