from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time_utils import utcnow_naive
from app.db.base import Base


class FarmerOlivePieceMetric(Base):
    __tablename__ = "farmer_olive_piece_metrics"
    __table_args__ = (
        UniqueConstraint("farmer_user_id", "season_year", "piece_label", name="uq_farmer_piece_year_label"),
        Index("ix_farmer_piece_metrics_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_piece_metrics_season_year", "season_year"),
        Index("ix_farmer_piece_metrics_piece_label", "piece_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    piece_label: Mapped[str] = mapped_column(String(120), nullable=False)
    harvested_kg: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tanks_20l: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
