from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister


def register_user(db: Session, payload: UserRegister) -> User:
    existing = db.scalar(select(User).where(User.phone == payload.phone))
    if existing:
        raise ValueError("Phone is already registered")

    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
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
