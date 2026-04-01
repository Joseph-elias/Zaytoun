from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.worker import WeekDay

BookingStatus = Literal[
    "pending_worker",
    "pending_farmer",
    "confirmed",
    "rejected",
    "pending",   # legacy
    "accepted",  # legacy
]


class BookingCreate(BaseModel):
    days: list[WeekDay] = Field(min_length=1, max_length=7)
    requested_men: int = Field(ge=0, le=100)
    requested_women: int = Field(ge=0, le=100)
    note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_team_size(self) -> "BookingCreate":
        if self.requested_men + self.requested_women < 1:
            raise ValueError("At least one person is required in booking request")
        self.days = list(dict.fromkeys(self.days))
        return self


class WorkerBookingResponse(BaseModel):
    action: Literal["accept", "reject", "propose"]
    requested_men: int | None = Field(default=None, ge=0, le=100)
    requested_women: int | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=300)


class FarmerBookingValidation(BaseModel):
    action: Literal["confirm", "reject"]


class BookingOut(BaseModel):
    id: UUID
    worker_id: UUID
    worker_name: str
    worker_phone: str
    worker_village: str
    farmer_user_id: UUID
    farmer_name: str
    farmer_phone: str
    day: WeekDay
    requested_men: int
    requested_women: int
    status: BookingStatus
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1200)


class BookingMessageOut(BaseModel):
    id: UUID
    booking_id: UUID
    sender_user_id: UUID
    sender_name: str
    sender_role: Literal["worker", "farmer"]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingEventOut(BaseModel):
    id: UUID
    booking_id: UUID
    actor_user_id: UUID
    actor_name: str
    actor_role: Literal["worker", "farmer"]
    action: str
    details: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
