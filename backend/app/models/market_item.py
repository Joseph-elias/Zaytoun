from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time_utils import utcnow_naive
from app.db.base import Base


class FarmerMarketItem(Base):
    __tablename__ = "farmer_market_items"
    __table_args__ = (
        Index("ix_farmer_market_items_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_market_items_is_active", "is_active"),
        Index("ix_farmer_market_items_item_name", "item_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(400), nullable=True)
    brand_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pickup_location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    unit_label: Mapped[str] = mapped_column(String(50), nullable=False)
    price_per_unit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_available: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    linked_inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("farmer_olive_inventory_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
