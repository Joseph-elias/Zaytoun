from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


SaleType = Literal["oil_tank", "raw_kg", "processed_container", "soap", "custom_item"]


class OliveSaleBase(BaseModel):
    season_id: UUID
    sold_on: date | None = None
    sale_type: SaleType = "oil_tank"

    tanks_sold: Decimal | None = Field(default=None, ge=0)
    price_per_tank: Decimal | None = Field(default=None, ge=0)

    raw_kg_sold: Decimal | None = Field(default=None, ge=0)
    price_per_kg: Decimal | None = Field(default=None, ge=0)

    containers_sold: Decimal | None = Field(default=None, ge=0)
    container_size_label: str | None = Field(default=None, min_length=1, max_length=120)
    kg_per_container: Decimal | None = Field(default=None, ge=0)
    price_per_container: Decimal | None = Field(default=None, ge=0)

    custom_inventory_item_id: UUID | None = None
    custom_item_name: str | None = Field(default=None, min_length=1, max_length=120)
    custom_quantity_sold: Decimal | None = Field(default=None, ge=0)
    custom_unit_label: str | None = Field(default=None, min_length=1, max_length=60)
    custom_price_per_unit: Decimal | None = Field(default=None, ge=0)
    custom_inventory_tanks_delta: Decimal | None = Field(default=None, ge=0)

    buyer: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=400)


class OliveSaleCreate(OliveSaleBase):
    @model_validator(mode="after")
    def validate_by_type(self) -> "OliveSaleCreate":
        if self.sale_type == "oil_tank":
            if self.tanks_sold is None or self.price_per_tank is None:
                raise ValueError("For oil_tank sale, tanks sold and price per tank are required")
        elif self.sale_type == "raw_kg":
            if self.raw_kg_sold is None or self.price_per_kg is None:
                raise ValueError("For raw_kg sale, kg sold and price per kg are required")
        elif self.sale_type == "processed_container":
            if self.containers_sold is None or self.kg_per_container is None or self.price_per_container is None or not self.container_size_label:
                raise ValueError("For processed_container sale, containers count, container size, kg per container and price per container are required")
        elif self.sale_type in ("soap", "custom_item"):
            if self.custom_quantity_sold is None:
                raise ValueError("For custom_item/soap sale, quantity is required")
            if self.custom_inventory_item_id is None and (not self.custom_item_name or not self.custom_unit_label or self.custom_price_per_unit is None):
                raise ValueError("For custom_item/soap sale, choose an inventory item or provide item name, unit, and price per unit")
        return self


class OliveSaleOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    season_id: UUID
    sold_on: date | None
    sale_type: SaleType

    tanks_sold: Decimal | None
    price_per_tank: Decimal | None

    raw_kg_sold: Decimal | None
    price_per_kg: Decimal | None

    containers_sold: Decimal | None
    container_size_label: str | None
    kg_per_container: Decimal | None
    price_per_container: Decimal | None

    custom_inventory_item_id: UUID | None
    custom_item_name: str | None
    custom_quantity_sold: Decimal | None
    custom_unit_label: str | None
    custom_price_per_unit: Decimal | None

    inventory_tanks_delta: Decimal
    total_revenue: Decimal
    buyer: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

