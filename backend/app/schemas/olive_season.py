from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


PressingCostMode = Literal["money", "oil_tanks"]


class OliveSeasonBase(BaseModel):
    season_year: int = Field(ge=2000, le=2100)
    land_pieces: int = Field(ge=1, le=200000)
    land_piece_name: str = Field(min_length=1, max_length=120)
    estimated_chonbol: Decimal | None = Field(default=None, ge=0)
    actual_chonbol: Decimal | None = Field(default=None, ge=0)
    kg_per_land_piece: Decimal | None = Field(default=None, ge=0)
    tanks_20l: int | None = Field(default=None, ge=0, le=200000)
    tanks_taken_home_20l: Decimal | None = Field(default=None, ge=0)
    pressing_cost_mode: PressingCostMode = "money"
    pressing_cost: Decimal | None = Field(default=None, ge=0)
    pressing_cost_oil_tanks_20l: Decimal | None = Field(default=None, ge=0)
    pressing_cost_oil_tank_unit_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class OliveSeasonCreate(OliveSeasonBase):
    @model_validator(mode="after")
    def validate_inputs(self) -> "OliveSeasonCreate":
        if self.actual_chonbol is not None and self.kg_per_land_piece is None:
            return self
        return self


class OliveSeasonUpdate(OliveSeasonBase):
    @model_validator(mode="after")
    def validate_inputs(self) -> "OliveSeasonUpdate":
        return self



class OliveSeasonTankPriceUpdate(BaseModel):
    unit_price: Decimal | None = Field(default=None, ge=0)
class OliveSeasonOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    season_year: int
    land_pieces: int
    land_piece_name: str
    estimated_chonbol: Decimal | None
    actual_chonbol: Decimal | None
    kg_per_land_piece: Decimal | None
    tanks_20l: int | None
    tanks_taken_home_20l: Decimal | None
    kg_needed_per_tank: Decimal | None
    pressing_cost_mode: PressingCostMode
    pressing_cost: Decimal | None
    pressing_cost_oil_tanks_20l: Decimal | None
    pressing_cost_oil_tank_unit_price: Decimal | None
    pressing_cost_money_equivalent: Decimal | None
    labor_cost_total: Decimal
    total_cost: Decimal
    sold_tanks: Decimal
    used_tanks: Decimal
    sales_revenue_total: Decimal
    profit: Decimal
    remaining_tanks: Decimal | None
    harvest_days: int
    worker_days: int
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

