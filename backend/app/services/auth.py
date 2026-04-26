from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.config import settings
from app.core.mfa_totp import generate_base32_secret, provisioning_uri, verify_totp
from app.core.time_utils import utcnow_naive
from app.models.booking import Booking
from app.models.booking_event import BookingEvent
from app.models.booking_message import BookingMessage
from app.models.user import User
from app.models.worker import Worker
from app.schemas.auth import (
    PasswordChangePayload,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserLogin,
    UserProfileUpdate,
    UserRegister,
)
from app.services.email import send_password_reset_code_email


PASSWORD_RESET_GENERIC_MESSAGE = "If the account exists, a password reset code has been generated."
PASSWORD_RESET_SUCCESS_MESSAGE = "Your password has been updated. You can now log in."
LOGIN_LOCKED_MESSAGE = "Account temporarily locked due to repeated failed login attempts."
MFA_REQUIRED_MESSAGE = "MFA code required."
MFA_INVALID_MESSAGE = "Invalid MFA code."


def register_user(db: Session, payload: UserRegister) -> User:
    existing = db.scalar(select(User).where(User.phone == payload.phone))
    if existing:
        raise ValueError("Phone is already registered")
    if payload.email:
        email_existing = db.scalar(select(User).where(User.email == payload.email))
        if email_existing:
            raise ValueError("Email is already registered")

    consent_recorded_at = datetime.now(timezone.utc)
    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        role=payload.role,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        terms_accepted_at=consent_recorded_at,
        data_consent_accepted_at=consent_recorded_at,
        consent_version=payload.consent_version,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLogin) -> tuple[User | None, str | None]:
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        return None, "invalid_credentials"

    if settings.auth_login_lockout_enabled and user.login_locked_until and user.login_locked_until > utcnow_naive():
        return None, "locked"

    if not verify_password(payload.password, user.password_hash):
        if settings.auth_login_lockout_enabled:
            user.login_failed_attempts = int(user.login_failed_attempts or 0) + 1
            if user.login_failed_attempts >= max(1, int(settings.auth_login_max_attempts)):
                user.login_locked_until = utcnow_naive() + timedelta(minutes=max(1, int(settings.auth_login_lockout_minutes)))
            db.commit()
        return None, "invalid_credentials"

    if int(user.login_failed_attempts or 0) > 0 or user.login_locked_until is not None:
        user.login_failed_attempts = 0
        user.login_locked_until = None
        db.commit()

    return user, None


def is_user_consent_current(user: User) -> bool:
    if not user.terms_accepted_at or not user.data_consent_accepted_at:
        return False
    return str(user.consent_version or "") == str(settings.auth_consent_version)


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def delete_user_account(db: Session, user: User) -> None:
    worker_ids = db.scalars(select(Worker.id).where(Worker.phone == user.phone)).all()

    if worker_ids:
        db.execute(delete(Booking).where(Booking.worker_id.in_(worker_ids)))
        db.execute(delete(Worker).where(Worker.id.in_(worker_ids)))

    farmer_booking_ids = db.scalars(select(Booking.id).where(Booking.farmer_user_id == user.id)).all()
    if farmer_booking_ids:
        db.execute(delete(BookingMessage).where(BookingMessage.booking_id.in_(farmer_booking_ids)))
        db.execute(delete(BookingEvent).where(BookingEvent.booking_id.in_(farmer_booking_ids)))
        db.execute(delete(Booking).where(Booking.id.in_(farmer_booking_ids)))

    db.execute(delete(BookingMessage).where(BookingMessage.sender_user_id == user.id))
    db.execute(delete(BookingEvent).where(BookingEvent.actor_user_id == user.id))

    db.delete(user)
    db.commit()


def update_user_profile(db: Session, user: User, payload: UserProfileUpdate) -> User:
    sensitive_change = payload.phone != user.phone or payload.email != user.email
    if sensitive_change:
        if not payload.current_password:
            raise ValueError("Current password is required to change phone or email")
        if not verify_password(payload.current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

    if payload.phone != user.phone:
        existing_phone = db.scalar(select(User).where(User.phone == payload.phone, User.id != user.id))
        if existing_phone:
            raise ValueError("Phone is already registered")

    if payload.email != user.email and payload.email:
        existing_email = db.scalar(select(User).where(User.email == payload.email, User.id != user.id))
        if existing_email:
            raise ValueError("Email is already registered")

    old_phone = user.phone
    user.full_name = payload.full_name
    user.phone = payload.phone
    user.email = payload.email

    if old_phone != payload.phone:
        workers = db.scalars(select(Worker).where(Worker.phone == old_phone)).all()
        for worker in workers:
            worker.phone = payload.phone

    db.commit()
    db.refresh(user)
    return user


def change_user_password(db: Session, user: User, payload: PasswordChangePayload) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise ValueError("Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    user.token_version = int(user.token_version or 0) + 1
    db.commit()


def request_password_reset(db: Session, payload: PasswordResetRequest) -> str | None:
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        return None

    now = utcnow_naive()
    expires_at = now + timedelta(minutes=settings.auth_password_reset_code_ttl_minutes)
    code = f"{secrets.randbelow(1_000_000):06d}"

    user.password_reset_code_hash = hash_password(code)
    user.password_reset_requested_at = now
    user.password_reset_expires_at = expires_at
    user.password_reset_attempts = 0
    db.commit()
    if user.email:
        send_password_reset_code_email(
            to_email=user.email,
            reset_code=code,
            ttl_minutes=settings.auth_password_reset_code_ttl_minutes,
        )

    return code


def confirm_password_reset(db: Session, payload: PasswordResetConfirm) -> bool:
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        return False

    now = utcnow_naive()

    if not user.password_reset_code_hash or not user.password_reset_expires_at:
        return False

    if user.password_reset_expires_at < now:
        return False

    if user.password_reset_attempts >= settings.auth_password_reset_max_attempts:
        return False

    if not verify_password(payload.reset_code, user.password_reset_code_hash):
        user.password_reset_attempts += 1
        db.commit()
        return False

    user.password_hash = hash_password(payload.new_password)
    user.token_version = int(user.token_version or 0) + 1
    user.password_reset_code_hash = None
    user.password_reset_requested_at = None
    user.password_reset_expires_at = None
    user.password_reset_attempts = 0
    db.commit()
    return True


def begin_mfa_setup(db: Session, user: User, current_password: str) -> tuple[str, str]:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")
    secret = generate_base32_secret()
    user.mfa_totp_pending_secret = secret
    db.commit()
    account_name = user.email or user.phone
    uri = provisioning_uri(
        secret=secret,
        account_name=account_name,
        issuer=settings.auth_mfa_totp_issuer,
        period_seconds=settings.auth_mfa_totp_period_seconds,
        digits=settings.auth_mfa_totp_digits,
    )
    return secret, uri


def enable_mfa(db: Session, user: User, otp_code: str) -> bool:
    pending = str(user.mfa_totp_pending_secret or "").strip()
    if not pending:
        return False
    ok = verify_totp(
        pending,
        otp_code,
        period_seconds=settings.auth_mfa_totp_period_seconds,
        digits=settings.auth_mfa_totp_digits,
        valid_window=settings.auth_mfa_totp_valid_window,
    )
    if not ok:
        return False
    user.mfa_totp_secret = pending
    user.mfa_totp_pending_secret = None
    user.mfa_enabled = True
    user.mfa_enabled_at = utcnow_naive()
    user.token_version = int(user.token_version or 0) + 1
    db.commit()
    return True


def is_mfa_code_valid(user: User, otp_code: str | None) -> bool:
    if not user.mfa_enabled:
        return True
    secret = str(user.mfa_totp_secret or "").strip()
    if not secret:
        return False
    if not otp_code:
        return False
    return verify_totp(
        secret,
        otp_code,
        period_seconds=settings.auth_mfa_totp_period_seconds,
        digits=settings.auth_mfa_totp_digits,
        valid_window=settings.auth_mfa_totp_valid_window,
    )


def disable_mfa(db: Session, user: User, current_password: str, otp_code: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")
    if not user.mfa_enabled:
        raise ValueError("MFA is not enabled")
    if not is_mfa_code_valid(user, otp_code):
        raise ValueError("Invalid MFA code")
    user.mfa_enabled = False
    user.mfa_enabled_at = None
    user.mfa_totp_secret = None
    user.mfa_totp_pending_secret = None
    user.token_version = int(user.token_version or 0) + 1
    db.commit()
