from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketOrder(Base):
    __tablename__ = "market_orders"
    __table_args__ = (
        Index("ix_market_orders_farmer_user_id", "farmer_user_id"),
        Index("ix_market_orders_customer_user_id", "customer_user_id"),
        Index("ix_market_orders_item_id", "market_item_id"),
        Index("ix_market_orders_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    market_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("farmer_market_items.id", ondelete="CASCADE"), nullable=False)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    item_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_label_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_ordered: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    pickup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    farmer_response_note: Mapped[str | None] = mapped_column(String(400), nullable=True)

    linked_inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("farmer_olive_inventory_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    inventory_reserved_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    inventory_shortage_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inventory_shortage_note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    pickup_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_review: Mapped[str | None] = mapped_column(String(800), nullable=True)
    customer_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    market_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_review: Mapped[str | None] = mapped_column(String(800), nullable=True)
    market_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
