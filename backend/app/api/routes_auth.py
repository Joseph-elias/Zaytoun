from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_allow_stale_consent
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthToken,
    ConsentReacceptPayload,
    PasswordChangePayload,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    UserLogin,
    UserOut,
    UserProfileUpdate,
    UserRegister,
)
from app.services.auth import (
    PASSWORD_RESET_GENERIC_MESSAGE,
    PASSWORD_RESET_SUCCESS_MESSAGE,
    authenticate_user,
    change_user_password,
    confirm_password_reset,
    delete_user_account,
    is_user_consent_current,
    register_user,
    request_password_reset,
    update_user_profile,
)

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

    token = create_access_token(subject=str(user.id), role=user.role, token_version=int(user.token_version or 0))
    consent_reaccept_required = not is_user_consent_current(user)
    return AuthToken(
        access_token=token,
        user=UserOut.model_validate(user),
        consent_reaccept_required=consent_reaccept_required,
        required_consent_version=settings.auth_consent_version if consent_reaccept_required else None,
    )


@router.get("/me", response_model=UserOut)
def me_endpoint(current_user: User = Depends(get_current_user_allow_stale_consent)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile_endpoint(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> UserOut:
    try:
        updated = update_user_profile(db, current_user, payload)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST if "password" in detail.lower() else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return UserOut.model_validate(updated)


@router.patch("/me/password", response_model=PasswordResetResponse)
def change_my_password_endpoint(
    payload: PasswordChangePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> PasswordResetResponse:
    try:
        change_user_password(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PasswordResetResponse(message="Password changed successfully.")


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def password_reset_request_endpoint(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> PasswordResetResponse:
    reset_code = request_password_reset(db, payload)
    response = PasswordResetResponse(message=PASSWORD_RESET_GENERIC_MESSAGE)

    if settings.auth_password_reset_dev_mode and reset_code:
        response.debug_reset_code = reset_code

    return response


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def password_reset_confirm_endpoint(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> PasswordResetResponse:
    ok = confirm_password_reset(db, payload)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code.",
        )
    return PasswordResetResponse(message=PASSWORD_RESET_SUCCESS_MESSAGE)


@router.patch("/consent", response_model=UserOut)
def reaccept_consent_endpoint(
    payload: ConsentReacceptPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> UserOut:
    if payload.consent_version != settings.auth_consent_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consent version mismatch. Required version is {settings.auth_consent_version}.",
        )

    now = datetime.now(timezone.utc)
    current_user.terms_accepted_at = now
    current_user.data_consent_accepted_at = now
    current_user.consent_version = payload.consent_version
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> Response:
    delete_user_account(db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
