from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RateType = Literal["day", "hour"]
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


class WorkerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=50)
    village: str = Field(min_length=2, max_length=120)
    men_count: int = Field(ge=0, le=100)
    women_count: int = Field(ge=0, le=100)
    rate_type: RateType
    men_rate_value: Decimal | None = Field(default=None, gt=0)
    women_rate_value: Decimal | None = Field(default=None, gt=0)
    overtime_open: bool = False
    overtime_price: Decimal | None = Field(default=None, gt=0)
    overtime_note: str | None = Field(default=None, max_length=300)
    available_days: list[WeekDay] = Field(default_factory=lambda: ALL_WEEK_DAYS.copy(), min_length=1, max_length=7)
    available: bool = True

    @field_validator("available_days")
    @classmethod
    def normalize_days(cls, days: list[WeekDay]) -> list[WeekDay]:
        return list(dict.fromkeys(days))

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

        return self


class WorkerAvailabilityUpdate(BaseModel):
    available: bool


class WorkerOut(BaseModel):
    id: UUID
    name: str
    phone: str
    village: str
    men_count: int
    women_count: int
    rate_type: RateType
    men_rate_value: Decimal | None
    women_rate_value: Decimal | None
    overtime_open: bool
    overtime_price: Decimal | None
    overtime_note: str | None
    available_days: list[WeekDay]
    available: bool
    created_at: datetime

    @field_validator("available_days", mode="before")
    @classmethod
    def parse_days(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [day for day in value.split(",") if day]
        if isinstance(value, list):
            return value
        return ALL_WEEK_DAYS.copy()

    model_config = ConfigDict(from_attributes=True)
