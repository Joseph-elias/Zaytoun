from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OliveLandPieceBase(BaseModel):
    piece_name: str = Field(min_length=1, max_length=120)
    season_year: int | None = Field(default=None, ge=2000, le=2100)


class OliveLandPieceCreate(OliveLandPieceBase):
    pass


class OliveLandPieceOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    piece_name: str
    season_year: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
