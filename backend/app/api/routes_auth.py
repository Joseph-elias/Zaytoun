from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_allow_stale_consent
from app.core.audit import (
    AUTH_ACCOUNT_DELETE,
    AUTH_CONSENT_REACCEPT,
    AUTH_LOGIN,
    AUTH_LOGIN_FAILED,
    AUTH_PASSWORD_CHANGED,
    AUTH_PASSWORD_RESET_CONFIRM,
    AUTH_PASSWORD_RESET_CONFIRM_FAILED,
    AUTH_PASSWORD_RESET_REQUEST,
    AUTH_PROFILE_UPDATED,
    AUTH_REGISTER,
    AUTH_REGISTER_FAILED,
    AUTH_MFA_SETUP,
    AUTH_MFA_SETUP_FAILED,
    AUTH_MFA_ENABLE,
    AUTH_MFA_ENABLE_FAILED,
    AUTH_MFA_DISABLE,
    AUTH_MFA_DISABLE_FAILED,
    emit_audit,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthToken,
    ConsentReacceptPayload,
    MfaDisablePayload,
    MfaEnablePayload,
    MfaSetupOut,
    MfaSetupPayload,
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
    LOGIN_LOCKED_MESSAGE,
    MFA_INVALID_MESSAGE,
    MFA_REQUIRED_MESSAGE,
    PASSWORD_RESET_GENERIC_MESSAGE,
    PASSWORD_RESET_SUCCESS_MESSAGE,
    authenticate_user,
    begin_mfa_setup,
    change_user_password,
    confirm_password_reset,
    delete_user_account,
    disable_mfa,
    enable_mfa,
    is_mfa_code_valid,
    is_user_consent_current,
    register_user,
    request_password_reset,
    update_user_profile,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_endpoint(payload: UserRegister, request: Request, db: Session = Depends(get_db)) -> UserOut:
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        emit_audit(
            AUTH_REGISTER_FAILED,
            request=request,
            metadata={"phone": payload.phone, "role": payload.role, "reason": str(exc)},
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    emit_audit(AUTH_REGISTER, request=request, actor_user_id=str(user.id), metadata={"role": user.role})
    return UserOut.model_validate(user)


@router.post("/login", response_model=AuthToken)
def login_endpoint(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> AuthToken:
    user, auth_error = authenticate_user(db, payload)
    if not user:
        emit_audit(AUTH_LOGIN_FAILED, request=request, metadata={"phone": payload.phone})
        if auth_error == "locked":
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=LOGIN_LOCKED_MESSAGE)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")
    if user.mfa_enabled and not payload.otp_code:
        emit_audit(AUTH_LOGIN_FAILED, request=request, actor_user_id=str(user.id), metadata={"reason": "mfa_required"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "mfa_required", "message": MFA_REQUIRED_MESSAGE},
        )
    if user.mfa_enabled and not is_mfa_code_valid(user, payload.otp_code):
        emit_audit(AUTH_LOGIN_FAILED, request=request, actor_user_id=str(user.id), metadata={"reason": "mfa_invalid"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MFA_INVALID_MESSAGE)

    token = create_access_token(subject=str(user.id), role=user.role, token_version=int(user.token_version or 0))
    consent_reaccept_required = not is_user_consent_current(user)
    emit_audit(
        AUTH_LOGIN,
        request=request,
        actor_user_id=str(user.id),
        metadata={"role": user.role, "consent_reaccept_required": consent_reaccept_required},
    )
    return AuthToken(
        access_token=token,
        user=UserOut.model_validate(user),
        consent_reaccept_required=consent_reaccept_required,
        required_consent_version=settings.auth_consent_version if consent_reaccept_required else None,
    )


@router.post("/mfa/setup", response_model=MfaSetupOut)
def setup_mfa_endpoint(
    payload: MfaSetupPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> MfaSetupOut:
    try:
        secret, uri = begin_mfa_setup(db, current_user, payload.current_password)
    except ValueError as exc:
        emit_audit(AUTH_MFA_SETUP_FAILED, request=request, actor_user_id=str(current_user.id), metadata={"reason": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    emit_audit(AUTH_MFA_SETUP, request=request, actor_user_id=str(current_user.id))
    return MfaSetupOut(
        secret=secret,
        otpauth_uri=uri,
        issuer=settings.auth_mfa_totp_issuer,
        account_name=current_user.email or current_user.phone,
    )


@router.post("/mfa/enable", response_model=PasswordResetResponse)
def enable_mfa_endpoint(
    payload: MfaEnablePayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> PasswordResetResponse:
    ok = enable_mfa(db, current_user, payload.otp_code)
    if not ok:
        emit_audit(AUTH_MFA_ENABLE_FAILED, request=request, actor_user_id=str(current_user.id), metadata={"reason": "invalid_code_or_no_pending_setup"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code or no pending MFA setup.")
    emit_audit(AUTH_MFA_ENABLE, request=request, actor_user_id=str(current_user.id))
    return PasswordResetResponse(message="MFA enabled successfully.")


@router.post("/mfa/disable", response_model=PasswordResetResponse)
def disable_mfa_endpoint(
    payload: MfaDisablePayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> PasswordResetResponse:
    try:
        disable_mfa(db, current_user, payload.current_password, payload.otp_code)
    except ValueError as exc:
        emit_audit(AUTH_MFA_DISABLE_FAILED, request=request, actor_user_id=str(current_user.id), metadata={"reason": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    emit_audit(AUTH_MFA_DISABLE, request=request, actor_user_id=str(current_user.id))
    return PasswordResetResponse(message="MFA disabled successfully.")


@router.get("/me", response_model=UserOut)
def me_endpoint(current_user: User = Depends(get_current_user_allow_stale_consent)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile_endpoint(
    payload: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> UserOut:
    old_phone = current_user.phone
    old_email = current_user.email
    try:
        updated = update_user_profile(db, current_user, payload)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST if "password" in detail.lower() else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=detail) from exc

    emit_audit(
        AUTH_PROFILE_UPDATED,
        request=request,
        actor_user_id=str(current_user.id),
        metadata={"phone_changed": payload.phone != old_phone, "email_changed": payload.email != old_email},
    )
    return UserOut.model_validate(updated)


@router.patch("/me/password", response_model=PasswordResetResponse)
def change_my_password_endpoint(
    payload: PasswordChangePayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> PasswordResetResponse:
    try:
        change_user_password(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    emit_audit(AUTH_PASSWORD_CHANGED, request=request, actor_user_id=str(current_user.id))
    return PasswordResetResponse(message="Password changed successfully.")


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def password_reset_request_endpoint(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)) -> PasswordResetResponse:
    reset_code = request_password_reset(db, payload)
    response = PasswordResetResponse(message=PASSWORD_RESET_GENERIC_MESSAGE)

    if settings.auth_password_reset_dev_mode and reset_code:
        response.debug_reset_code = reset_code

    emit_audit(
        AUTH_PASSWORD_RESET_REQUEST,
        request=request,
        metadata={"phone": payload.phone, "code_issued": bool(reset_code)},
    )
    return response


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def password_reset_confirm_endpoint(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)) -> PasswordResetResponse:
    ok = confirm_password_reset(db, payload)
    if not ok:
        emit_audit(AUTH_PASSWORD_RESET_CONFIRM_FAILED, request=request, metadata={"phone": payload.phone})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code.",
        )
    emit_audit(AUTH_PASSWORD_RESET_CONFIRM, request=request, metadata={"phone": payload.phone})
    return PasswordResetResponse(message=PASSWORD_RESET_SUCCESS_MESSAGE)


@router.patch("/consent", response_model=UserOut)
def reaccept_consent_endpoint(
    payload: ConsentReacceptPayload,
    request: Request,
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
    emit_audit(
        AUTH_CONSENT_REACCEPT,
        request=request,
        actor_user_id=str(current_user.id),
        metadata={"consent_version": payload.consent_version},
    )
    return UserOut.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_stale_consent),
) -> Response:
    emit_audit(AUTH_ACCOUNT_DELETE, request=request, actor_user_id=str(current_user.id), metadata={"role": current_user.role})
    delete_user_account(db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
