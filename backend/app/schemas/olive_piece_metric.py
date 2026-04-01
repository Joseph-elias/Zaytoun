from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OlivePieceMetricBase(BaseModel):
    season_year: int = Field(ge=2000, le=2100)
    piece_label: str = Field(min_length=1, max_length=120)
    harvested_kg: Decimal = Field(ge=0)
    tanks_20l: int | None = Field(default=None, ge=0, le=200000)
    notes: str | None = Field(default=None, max_length=400)


class OlivePieceMetricCreate(OlivePieceMetricBase):
    pass


class OlivePieceMetricUpdate(OlivePieceMetricBase):
    pass


class OlivePieceMetricOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    season_year: int
    piece_label: str
    harvested_kg: Decimal
    tanks_20l: int | None
    kg_needed_per_tank: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
