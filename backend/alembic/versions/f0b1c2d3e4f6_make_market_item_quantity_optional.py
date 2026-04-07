"""make_market_item_quantity_optional

Revision ID: f0b1c2d3e4f6
Revises: e9a1b2c3d4f5
Create Date: 2026-04-07 18:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f0b1c2d3e4f6"
down_revision: Union[str, None] = "e9a1b2c3d4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"]: col for col in inspector.get_columns("farmer_market_items")}

    if "quantity_available" in columns and not columns["quantity_available"].get("nullable", False):
        with op.batch_alter_table("farmer_market_items") as batch_op:
            batch_op.alter_column(
                "quantity_available",
                existing_type=sa.Numeric(precision=12, scale=2),
                nullable=True,
                existing_nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"]: col for col in inspector.get_columns("farmer_market_items")}

    op.execute(sa.text("UPDATE farmer_market_items SET quantity_available = 0 WHERE quantity_available IS NULL"))

    if "quantity_available" in columns and columns["quantity_available"].get("nullable", False):
        with op.batch_alter_table("farmer_market_items") as batch_op:
            batch_op.alter_column(
                "quantity_available",
                existing_type=sa.Numeric(precision=12, scale=2),
                nullable=False,
                existing_nullable=True,
            )
