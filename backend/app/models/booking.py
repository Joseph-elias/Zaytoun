from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_worker_id_day", "worker_id", "day"),
        Index("ix_bookings_worker_id_work_date", "worker_id", "work_date"),
        Index("ix_bookings_worker_id_work_date_work_slot", "worker_id", "work_date", "work_slot"),
        Index("ix_bookings_farmer_user_id", "farmer_user_id"),
        Index("ix_bookings_season_id", "season_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("farmer_olive_seasons.id", ondelete="SET NULL"), nullable=True)
    work_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    work_slot: Mapped[str] = mapped_column(String(20), nullable=False, default="full_day")
    day: Mapped[str | None] = mapped_column(String(10), nullable=True)  # legacy monday..sunday
    requested_men: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requested_women: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


