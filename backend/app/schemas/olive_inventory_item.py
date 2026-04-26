from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OliveInventoryItemBase(BaseModel):
    inventory_year: int = Field(default_factory=lambda: datetime.now(timezone.utc).year, ge=2000, le=2100)
    item_name: str = Field(min_length=1, max_length=120)
    unit_label: str = Field(min_length=1, max_length=60)
    quantity_on_hand: Decimal = Field(ge=0)
    quantity_pending: Decimal = Field(default=0, ge=0)
    default_price_per_unit: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=400)


class OliveInventoryItemCreate(OliveInventoryItemBase):
    pass


class OliveInventoryItemUpdate(BaseModel):
    inventory_year: int | None = Field(default=None, ge=2000, le=2100)
    item_name: str | None = Field(default=None, min_length=1, max_length=120)
    unit_label: str | None = Field(default=None, min_length=1, max_length=60)
    quantity_on_hand: Decimal | None = Field(default=None, ge=0)
    quantity_pending: Decimal | None = Field(default=None, ge=0)
    default_price_per_unit: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=400)


class OliveInventoryCarryOverPayload(BaseModel):
    from_year: int = Field(ge=2000, le=2100)
    to_year: int = Field(ge=2000, le=2100)


class OliveInventoryCarryOverOut(BaseModel):
    copied_count: int


class OliveInventoryItemOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    inventory_year: int
    item_name: str
    unit_label: str
    quantity_on_hand: Decimal
    quantity_pending: Decimal
    default_price_per_unit: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
