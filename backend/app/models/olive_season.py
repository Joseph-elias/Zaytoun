from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmerOliveSeason(Base):
    __tablename__ = "farmer_olive_seasons"
    __table_args__ = (
        UniqueConstraint("farmer_user_id", "season_year", "land_piece_name", name="uq_farmer_olive_seasons_farmer_year_piece"),
        Index("ix_farmer_olive_seasons_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_olive_seasons_season_year", "season_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    land_pieces: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    land_piece_name: Mapped[str] = mapped_column(String(120), nullable=False)
    estimated_chonbol: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_chonbol: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    kg_per_land_piece: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tanks_20l: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tanks_taken_home_20l: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    pressing_cost_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="money")
    pressing_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    pressing_cost_oil_tanks_20l: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
