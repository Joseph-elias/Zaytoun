from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # worker | farmer | customer
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    store_banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    store_about: Mapped[str | None] = mapped_column(String(600), nullable=True)
    store_opening_hours: Mapped[str | None] = mapped_column(String(180), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
