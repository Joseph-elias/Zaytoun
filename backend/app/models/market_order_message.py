from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time_utils import utcnow_naive
from app.db.base import Base


class MarketOrderMessage(Base):
    __tablename__ = "market_order_messages"
    __table_args__ = (
        Index("ix_market_order_messages_order_id", "market_order_id"),
        Index("ix_market_order_messages_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    market_order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("market_orders.id", ondelete="CASCADE"), nullable=False)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(String(1200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
