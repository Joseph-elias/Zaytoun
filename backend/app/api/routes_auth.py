from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import AuthToken, UserLogin, UserOut, UserRegister
from app.services.auth import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_endpoint(payload: UserRegister, db: Session = Depends(get_db)) -> UserOut:
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserOut.model_validate(user)


@router.post("/login", response_model=AuthToken)
def login_endpoint(payload: UserLogin, db: Session = Depends(get_db)) -> AuthToken:
    user = authenticate_user(db, payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")

    token = create_access_token(subject=str(user.id), role=user.role)
    return AuthToken(access_token=token, user=UserOut.model_validate(user))
