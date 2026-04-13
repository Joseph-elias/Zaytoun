from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RateType = Literal["day", "hour"]
WorkSlotType = Literal["full_day", "extra_time"]
WeekDay = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ALL_WEEK_DAYS: list[WeekDay] = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


class WorkerAvailabilityWindowIn(BaseModel):
    work_date: date
    slot_type: WorkSlotType


class WorkerAvailabilityWindowOut(BaseModel):
    work_date: date
    slot_type: WorkSlotType


class WorkerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=50)
    village: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    men_count: int = Field(ge=0, le=100)
    women_count: int = Field(ge=0, le=100)
    rate_type: RateType
    men_rate_value: Decimal | None = Field(default=None, gt=0)
    women_rate_value: Decimal | None = Field(default=None, gt=0)
    overtime_open: bool = False
    overtime_price: Decimal | None = Field(default=None, gt=0)
    overtime_note: str | None = Field(default=None, max_length=300)
    available_dates: list[date] = Field(default_factory=list, max_length=365)
    availability_windows: list["WorkerAvailabilityWindowIn"] = Field(default_factory=list, max_length=730)
    available: bool = True

    @field_validator("available_dates")
    @classmethod
    def normalize_dates(cls, values: list[date]) -> list[date]:
        return sorted(set(values))

    @field_validator("availability_windows")
    @classmethod
    def normalize_windows(cls, values: list["WorkerAvailabilityWindowIn"]) -> list["WorkerAvailabilityWindowIn"]:
        deduped: dict[tuple[date, WorkSlotType], WorkerAvailabilityWindowIn] = {}
        for item in values:
            deduped[(item.work_date, item.slot_type)] = item
        return sorted(deduped.values(), key=lambda row: (row.work_date, row.slot_type))

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_business_rules(self) -> "WorkerCreate":
        if self.men_count + self.women_count < 1:
            raise ValueError("At least one worker is required (men_count + women_count >= 1)")

        if self.men_count > 0 and self.men_rate_value is None:
            raise ValueError("men_rate_value is required when men_count is greater than 0")

        if self.men_count == 0 and self.men_rate_value is not None:
            raise ValueError("men_rate_value must be empty when men_count is 0")

        if self.women_count > 0 and self.women_rate_value is None:
            raise ValueError("women_rate_value is required when women_count is greater than 0")

        if self.women_count == 0 and self.women_rate_value is not None:
            raise ValueError("women_rate_value must be empty when women_count is 0")

        if self.overtime_open and self.overtime_price is None:
            raise ValueError("overtime_price is required when overtime_open is true")

        if not self.overtime_open and self.overtime_price is not None:
            raise ValueError("overtime_price must be empty when overtime_open is false")

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if not self.available_dates and not self.availability_windows:
            raise ValueError("Select at least one availability window or available date")

        return self


class WorkerUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    village: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    men_count: int = Field(ge=0, le=100)
    women_count: int = Field(ge=0, le=100)
    rate_type: RateType
    men_rate_value: Decimal | None = Field(default=None, gt=0)
    women_rate_value: Decimal | None = Field(default=None, gt=0)
    overtime_open: bool = False
    overtime_price: Decimal | None = Field(default=None, gt=0)
    overtime_note: str | None = Field(default=None, max_length=300)
    available_dates: list[date] = Field(default_factory=list, max_length=365)
    availability_windows: list["WorkerAvailabilityWindowIn"] = Field(default_factory=list, max_length=730)

    @field_validator("available_dates")
    @classmethod
    def normalize_dates(cls, values: list[date]) -> list[date]:
        return sorted(set(values))

    @field_validator("availability_windows")
    @classmethod
    def normalize_windows(cls, values: list["WorkerAvailabilityWindowIn"]) -> list["WorkerAvailabilityWindowIn"]:
        deduped: dict[tuple[date, WorkSlotType], WorkerAvailabilityWindowIn] = {}
        for item in values:
            deduped[(item.work_date, item.slot_type)] = item
        return sorted(deduped.values(), key=lambda row: (row.work_date, row.slot_type))

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_business_rules(self) -> "WorkerUpdate":
        if self.men_count + self.women_count < 1:
            raise ValueError("At least one worker is required (men_count + women_count >= 1)")

        if self.men_count > 0 and self.men_rate_value is None:
            raise ValueError("men_rate_value is required when men_count is greater than 0")

        if self.men_count == 0 and self.men_rate_value is not None:
            raise ValueError("men_rate_value must be empty when men_count is 0")

        if self.women_count > 0 and self.women_rate_value is None:
            raise ValueError("women_rate_value is required when women_count is greater than 0")

        if self.women_count == 0 and self.women_rate_value is not None:
            raise ValueError("women_rate_value must be empty when women_count is 0")

        if self.overtime_open and self.overtime_price is None:
            raise ValueError("overtime_price is required when overtime_open is true")

        if not self.overtime_open and self.overtime_price is not None:
            raise ValueError("overtime_price must be empty when overtime_open is false")

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if not self.available_dates and not self.availability_windows:
            raise ValueError("Select at least one availability window or available date")

        return self


class WorkerAvailabilityUpdate(BaseModel):
    available: bool


class WorkerOut(BaseModel):
    id: UUID
    name: str
    phone: str
    village: str
    address: str | None
    latitude: float | None
    longitude: float | None
    men_count: int
    women_count: int
    rate_type: RateType
    men_rate_value: Decimal | None
    women_rate_value: Decimal | None
    overtime_open: bool
    overtime_price: Decimal | None
    overtime_note: str | None
    available_dates: list[date]
    availability_windows: list["WorkerAvailabilityWindowOut"] = Field(default_factory=list)
    available: bool
    remaining_men_count: int | None = None
    remaining_women_count: int | None = None
    distance_km: float | None = None
    created_at: datetime

    @field_validator("available_dates", mode="before")
    @classmethod
    def parse_dates(cls, value: object) -> list[date]:
        if isinstance(value, str):
            raw = [token for token in value.split(",") if token]
            parsed: list[date] = []
            for token in raw:
                try:
                    parsed.append(date.fromisoformat(token))
                except ValueError:
                    continue
            return sorted(set(parsed))
        if isinstance(value, list):
            return sorted(set(value))
        return []

    @field_validator("availability_windows", mode="before")
    @classmethod
    def parse_availability_windows(cls, value: object) -> list["WorkerAvailabilityWindowOut"]:
        if isinstance(value, list):
            normalized: list[WorkerAvailabilityWindowOut] = []
            for item in value:
                if isinstance(item, WorkerAvailabilityWindowOut):
                    normalized.append(item)
                    continue
                if isinstance(item, dict):
                    normalized.append(WorkerAvailabilityWindowOut.model_validate(item))
                    continue
                work_date = getattr(item, "work_date", None)
                slot_type = getattr(item, "slot_type", None)
                if work_date is None or slot_type is None:
                    continue
                normalized.append(WorkerAvailabilityWindowOut(work_date=work_date, slot_type=slot_type))
            normalized.sort(key=lambda row: (row.work_date, row.slot_type))
            return normalized
        return []

    model_config = ConfigDict(from_attributes=True)
