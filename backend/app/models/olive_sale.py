from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmerOliveSale(Base):
    __tablename__ = "farmer_olive_sales"
    __table_args__ = (
        Index("ix_farmer_olive_sales_farmer_user_id", "farmer_user_id"),
        Index("ix_farmer_olive_sales_season_id", "season_id"),
        Index("ix_farmer_olive_sales_sold_on", "sold_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("farmer_olive_seasons.id", ondelete="CASCADE"), nullable=False)
    sold_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    sale_type: Mapped[str] = mapped_column(String(30), nullable=False, default="oil_tank")

    tanks_sold: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_per_tank: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    raw_kg_sold: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_per_kg: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    containers_sold: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    container_size_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    kg_per_container: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_per_container: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    custom_inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("farmer_olive_inventory_items.id", ondelete="SET NULL"), nullable=True)
    custom_item_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    custom_quantity_sold: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    custom_unit_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    custom_price_per_unit: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    inventory_tanks_delta: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    buyer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
