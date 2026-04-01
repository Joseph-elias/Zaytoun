from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RoleType = Literal["worker", "farmer"]


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=50)
    role: RoleType
    password: str = Field(min_length=6, max_length=128)
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

    @model_validator(mode="after")
    def validate_coordinates_pair(self) -> "UserRegister":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


class UserLogin(BaseModel):
    phone: str = Field(min_length=4, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: UUID
    full_name: str
    phone: str
    role: RoleType
    address: str | None
    latitude: float | None
    longitude: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
