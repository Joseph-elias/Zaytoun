from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (
        Index("ix_workers_village_available", "village", "available"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    village: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    men_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    women_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_type: Mapped[str] = mapped_column(String(10), nullable=False)  # day | hour
    men_rate_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    women_rate_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    overtime_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    overtime_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    overtime_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, index=True, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
