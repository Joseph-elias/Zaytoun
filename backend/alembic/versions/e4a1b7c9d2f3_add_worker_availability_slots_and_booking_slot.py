"""add_worker_availability_slots_and_booking_slot

Revision ID: e4a1b7c9d2f3
Revises: d1a7c9e4b2f5
Create Date: 2026-04-13 20:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4a1b7c9d2f3"
down_revision: Union[str, None] = "d1a7c9e4b2f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    booking_columns = _column_names("bookings")
    if "work_slot" not in booking_columns:
        with op.batch_alter_table("bookings") as batch_op:
            batch_op.add_column(sa.Column("work_slot", sa.String(length=20), nullable=True))
        op.execute(sa.text("UPDATE bookings SET work_slot = 'full_day' WHERE work_slot IS NULL OR work_slot = ''"))
        with op.batch_alter_table("bookings") as batch_op:
            batch_op.alter_column("work_slot", existing_type=sa.String(length=20), nullable=False)

    booking_indexes = _index_names("bookings")
    if "ix_bookings_worker_id_work_date_work_slot" not in booking_indexes:
        op.create_index(
            "ix_bookings_worker_id_work_date_work_slot",
            "bookings",
            ["worker_id", "work_date", "work_slot"],
        )

    if "worker_availability_slots" not in _table_names():
        op.create_table(
            "worker_availability_slots",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("worker_id", sa.Uuid(), nullable=False),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("slot_type", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    slot_indexes = _index_names("worker_availability_slots")
    if "ix_worker_availability_slots_worker_date" not in slot_indexes:
        op.create_index(
            "ix_worker_availability_slots_worker_date",
            "worker_availability_slots",
            ["worker_id", "work_date"],
        )
    if "ux_worker_availability_slots_worker_date_slot" not in slot_indexes:
        op.create_index(
            "ux_worker_availability_slots_worker_date_slot",
            "worker_availability_slots",
            ["worker_id", "work_date", "slot_type"],
            unique=True,
        )


def downgrade() -> None:
    if "worker_availability_slots" in _table_names():
        op.drop_index("ux_worker_availability_slots_worker_date_slot", table_name="worker_availability_slots")
        op.drop_index("ix_worker_availability_slots_worker_date", table_name="worker_availability_slots")
        op.drop_table("worker_availability_slots")

    booking_indexes = _index_names("bookings")
    if "ix_bookings_worker_id_work_date_work_slot" in booking_indexes:
        op.drop_index("ix_bookings_worker_id_work_date_work_slot", table_name="bookings")

    booking_columns = _column_names("bookings")
    if "work_slot" in booking_columns:
        with op.batch_alter_table("bookings") as batch_op:
            batch_op.drop_column("work_slot")
