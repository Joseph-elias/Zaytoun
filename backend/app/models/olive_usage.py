from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmerOliveUsage(Base):
    __tablename__ = "farmer_olive_usages"
    __table_args__ = (
        Index("ix_farmer_olive_usages_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_olive_usages_season_id", "season_id"),
        Index("ix_farmer_olive_usages_used_on", "used_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("farmer_olive_seasons.id", ondelete="CASCADE"), nullable=False)
    used_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    tanks_used: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    usage_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
