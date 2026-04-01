"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-01 19:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)

    op.create_table(
        "workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("village", sa.String(length=120), nullable=False),
        sa.Column("men_count", sa.Integer(), nullable=False),
        sa.Column("women_count", sa.Integer(), nullable=False),
        sa.Column("rate_type", sa.String(length=10), nullable=False),
        sa.Column("men_rate_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("women_rate_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("overtime_open", sa.Boolean(), nullable=False),
        sa.Column("overtime_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("overtime_note", sa.String(length=300), nullable=True),
        sa.Column("available_days", sa.String(length=120), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workers_available"), "workers", ["available"], unique=False)
    op.create_index(op.f("ix_workers_village"), "workers", ["village"], unique=False)
    op.create_index("ix_workers_village_available", "workers", ["village", "available"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column("farmer_user_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("requested_men", sa.Integer(), nullable=False),
        sa.Column("requested_women", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_farmer_user_id", "bookings", ["farmer_user_id"], unique=False)
    op.create_index("ix_bookings_worker_id_day", "bookings", ["worker_id", "day"], unique=False)

    op.create_table(
        "booking_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.String(length=1200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "booking_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("details", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("booking_events")
    op.drop_table("booking_messages")
    op.drop_index("ix_bookings_worker_id_day", table_name="bookings")
    op.drop_index("ix_bookings_farmer_user_id", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_workers_village_available", table_name="workers")
    op.drop_index(op.f("ix_workers_village"), table_name="workers")
    op.drop_index(op.f("ix_workers_available"), table_name="workers")
    op.drop_table("workers")
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_table("users")
