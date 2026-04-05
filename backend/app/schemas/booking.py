from datetime import date, datetime
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


class BookingRequestItem(BaseModel):
    work_date: date
    requested_men: int = Field(ge=0, le=100)
    requested_women: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_team_size(self) -> "BookingRequestItem":
        if self.requested_men + self.requested_women < 1:
            raise ValueError("At least one person is required per date request")
        return self


class BookingCreate(BaseModel):
    season_id: UUID | None = None
    requests: list[BookingRequestItem] = Field(min_length=1, max_length=31)
    note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_single_date_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if "requests" in data:
            return data

        work_date = data.get("work_date")
        requested_men = data.get("requested_men")
        requested_women = data.get("requested_women")
        if work_date is None or requested_men is None or requested_women is None:
            return data

        updated = dict(data)
        updated["requests"] = [
            {
                "work_date": work_date,
                "requested_men": requested_men,
                "requested_women": requested_women,
            }
        ]
        return updated

    @model_validator(mode="after")
    def validate_unique_dates(self) -> "BookingCreate":
        dates = [item.work_date for item in self.requests]
        if len(set(dates)) != len(dates):
            raise ValueError("Duplicate dates are not allowed in one booking request")
        return self


class WorkerBookingResponse(BaseModel):
    action: Literal["accept", "reject", "propose"]
    requested_men: int | None = Field(default=None, ge=0, le=100)
    requested_women: int | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=300)


class FarmerBookingValidation(BaseModel):
    action: Literal["confirm", "reject"]


class BookingProposalUpdate(BaseModel):
    work_date: date | None = None
    requested_men: int | None = Field(default=None, ge=0, le=100)
    requested_women: int | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_has_change(self) -> "BookingProposalUpdate":
        if self.work_date is None and self.requested_men is None and self.requested_women is None and self.note is None:
            raise ValueError("At least one field must be provided")
        return self


class BookingOut(BaseModel):
    id: UUID
    season_id: UUID | None
    worker_id: UUID
    worker_name: str
    worker_phone: str
    worker_village: str
    farmer_user_id: UUID
    farmer_name: str
    farmer_phone: str
    work_date: date | None
    day: WeekDay | None
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

