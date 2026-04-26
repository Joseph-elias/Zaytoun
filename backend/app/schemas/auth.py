from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RoleType = Literal["worker", "farmer", "customer"]


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=50)
    email: str | None = Field(default=None, min_length=6, max_length=255)
    role: RoleType
    password: str = Field(min_length=6, max_length=128)
    terms_accepted: bool
    data_consent_accepted: bool
    consent_version: str = Field(default="2026-04-13", min_length=3, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Invalid email format")
        return cleaned

    @model_validator(mode="after")
    def validate_coordinates_pair(self) -> "UserRegister":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if not self.terms_accepted:
            raise ValueError("Terms & Conditions must be accepted")
        if not self.data_consent_accepted:
            raise ValueError("Data consent must be accepted")
        return self


class UserLogin(BaseModel):
    phone: str = Field(min_length=4, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    legal_acknowledged: bool
    otp_code: str | None = Field(default=None, min_length=6, max_length=8)

    @model_validator(mode="after")
    def validate_legal_acknowledged(self) -> "UserLogin":
        if not self.legal_acknowledged:
            raise ValueError("Terms & Conditions and Data Consent Policy must be acknowledged")
        return self


class UserOut(BaseModel):
    id: UUID
    full_name: str
    phone: str
    email: str | None
    role: RoleType
    address: str | None
    latitude: float | None
    longitude: float | None
    terms_accepted_at: datetime | None
    data_consent_accepted_at: datetime | None
    consent_version: str | None
    mfa_enabled: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    consent_reaccept_required: bool = False
    required_consent_version: str | None = None


class MfaSetupPayload(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    issuer: str
    account_name: str


class MfaEnablePayload(BaseModel):
    otp_code: str = Field(min_length=6, max_length=8)


class MfaDisablePayload(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    otp_code: str = Field(min_length=6, max_length=8)


class ConsentReacceptPayload(BaseModel):
    legal_acknowledged: bool
    terms_accepted: bool
    data_consent_accepted: bool
    consent_version: str = Field(min_length=3, max_length=32)

    @model_validator(mode="after")
    def validate_flags(self) -> "ConsentReacceptPayload":
        if not self.legal_acknowledged:
            raise ValueError("Legal acknowledgement is required")
        if not self.terms_accepted:
            raise ValueError("Terms & Conditions must be accepted")
        if not self.data_consent_accepted:
            raise ValueError("Data consent must be accepted")
        return self


class PasswordResetRequest(BaseModel):
    phone: str = Field(min_length=4, max_length=50)


class PasswordResetConfirm(BaseModel):
    phone: str = Field(min_length=4, max_length=50)
    reset_code: str = Field(min_length=6, max_length=12)
    new_password: str = Field(min_length=6, max_length=128)


class PasswordResetResponse(BaseModel):
    message: str
    debug_reset_code: str | None = None


class UserProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=50)
    email: str | None = Field(default=None, min_length=6, max_length=255)
    current_password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("full_name is too short")
        return cleaned

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("phone is too short")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Invalid email format")
        return cleaned


class PasswordChangePayload(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def validate_passwords_differ(self) -> "PasswordChangePayload":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self
