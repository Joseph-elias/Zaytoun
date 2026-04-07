from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmerOliveInventoryItem(Base):
    __tablename__ = "farmer_olive_inventory_items"
    __table_args__ = (
        Index("ix_farmer_olive_inventory_items_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_olive_inventory_items_name", "item_name"),
        Index("ix_farmer_olive_inventory_items_year", "inventory_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    inventory_year: Mapped[int] = mapped_column(Integer, nullable=False, default=lambda: datetime.utcnow().year)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_label: Mapped[str] = mapped_column(String(60), nullable=False)
    quantity_on_hand: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    quantity_pending: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    default_price_per_unit: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
