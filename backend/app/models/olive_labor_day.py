from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmerOliveLaborDay(Base):
    __tablename__ = "farmer_olive_labor_days"
    __table_args__ = (
        UniqueConstraint("farmer_user_id", "season_id", "work_date", name="uq_farmer_labor_day_once"),
        Index("ix_farmer_labor_days_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_labor_days_season_id", "season_id"),
        Index("ix_farmer_labor_days_work_date", "work_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("farmer_olive_seasons.id", ondelete="CASCADE"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    men_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    women_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    men_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    women_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
