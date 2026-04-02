from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmerOliveLandPiece(Base):
    __tablename__ = "farmer_olive_land_pieces"
    __table_args__ = (
        Index("ix_farmer_olive_land_pieces_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_olive_land_pieces_name", "piece_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    piece_name: Mapped[str] = mapped_column(String(120), nullable=False)
    season_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
