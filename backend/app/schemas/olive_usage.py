from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OliveUsageBase(BaseModel):
    season_id: UUID
    used_on: date | None = None
    tanks_used: Decimal = Field(ge=0)
    usage_type: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=400)


class OliveUsageCreate(OliveUsageBase):
    pass


class OliveUsageOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    season_id: UUID
    used_on: date | None
    tanks_used: Decimal
    usage_type: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
