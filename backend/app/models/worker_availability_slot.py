from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkerAvailabilitySlot(Base):
    __tablename__ = "worker_availability_slots"
    __table_args__ = (
        Index("ix_worker_availability_slots_worker_date", "worker_id", "work_date"),
        Index(
            "ux_worker_availability_slots_worker_date_slot",
            "worker_id",
            "work_date",
            "slot_type",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_type: Mapped[str] = mapped_column(String(20), nullable=False)  # full_day | extra_time
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    worker = relationship("Worker", back_populates="availability_slots")
