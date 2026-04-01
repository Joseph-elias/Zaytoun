from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.booking import Booking
from app.models.booking_event import BookingEvent
from app.models.booking_message import BookingMessage
from app.models.user import User
from app.models.worker import Worker
from app.schemas.auth import UserLogin, UserRegister


def register_user(db: Session, payload: UserRegister) -> User:
    existing = db.scalar(select(User).where(User.phone == payload.phone))
    if existing:
        raise ValueError("Phone is already registered")

    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLogin) -> User | None:
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        return None

    if not verify_password(payload.password, user.password_hash):
        return None

    return user


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
