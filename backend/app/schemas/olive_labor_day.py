from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OliveLaborDayBase(BaseModel):
    season_id: UUID
    work_date: date
    men_count: int = Field(default=0, ge=0, le=2000)
    women_count: int = Field(default=0, ge=0, le=2000)
    men_rate: Decimal = Field(default=Decimal("0"), ge=0)
    women_rate: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = Field(default=None, max_length=400)


class OliveLaborDayCreate(OliveLaborDayBase):
    pass


class OliveLaborDayOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    season_id: UUID
    work_date: date
    men_count: int
    women_count: int
    men_rate: Decimal
    women_rate: Decimal
    total_day_cost: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
