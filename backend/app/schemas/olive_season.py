from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OliveSeasonBase(BaseModel):
    season_year: int = Field(ge=2000, le=2100)
    land_pieces: int = Field(ge=1, le=200000)
    land_piece_name: str = Field(min_length=1, max_length=120)
    estimated_chonbol: Decimal | None = Field(default=None, ge=0)
    actual_chonbol: Decimal | None = Field(default=None, ge=0)
    kg_per_land_piece: Decimal | None = Field(default=None, ge=0)
    tanks_20l: int | None = Field(default=None, ge=0, le=200000)
    notes: str | None = Field(default=None, max_length=500)


class OliveSeasonCreate(OliveSeasonBase):
    @model_validator(mode="after")
    def validate_inputs(self) -> "OliveSeasonCreate":
        if self.actual_chonbol is not None and self.kg_per_land_piece is None:
            # allow empty, frontend can still compute later
            return self
        return self


class OliveSeasonUpdate(OliveSeasonBase):
    pass


class OliveSeasonOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    season_year: int
    land_pieces: int
    land_piece_name: str | None
    estimated_chonbol: Decimal | None
    actual_chonbol: Decimal | None
    kg_per_land_piece: Decimal | None
    tanks_20l: int | None
    kg_needed_per_tank: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
