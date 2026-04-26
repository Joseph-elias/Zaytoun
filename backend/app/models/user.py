from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time_utils import utcnow_naive
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # worker | farmer | customer
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    store_banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    store_about: Mapped[str | None] = mapped_column(String(600), nullable=True)
    store_opening_hours: Mapped[str | None] = mapped_column(String(180), nullable=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_reset_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    password_reset_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    password_reset_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    login_failed_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    login_locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    mfa_enabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mfa_totp_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mfa_totp_pending_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    token_version: Mapped[int] = mapped_column(nullable=False, default=0)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
