from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


RoleType = Literal["worker", "farmer"]


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=50)
    role: RoleType
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    phone: str = Field(min_length=4, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: UUID
    full_name: str
    phone: str
    role: RoleType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
