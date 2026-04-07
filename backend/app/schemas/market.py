from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


OrderStatus = Literal["pending", "validated", "rejected"]


class MarketItemBase(BaseModel):
    item_name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    unit_label: str = Field(min_length=1, max_length=50)
    price_per_unit: Decimal = Field(gt=0)
    quantity_available: Decimal = Field(ge=0)
    is_active: bool = True


class MarketItemCreate(MarketItemBase):
    pass


class MarketItemUpdate(BaseModel):
    item_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    unit_label: str | None = Field(default=None, min_length=1, max_length=50)
    price_per_unit: Decimal | None = Field(default=None, gt=0)
    quantity_available: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class MarketItemOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    farmer_name: str
    item_name: str
    description: str | None
    unit_label: str
    price_per_unit: Decimal
    quantity_available: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketOrderCreate(BaseModel):
    market_item_id: UUID
    quantity_ordered: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=400)


class MarketOrderFarmerValidation(BaseModel):
    action: Literal["validate", "reject"]
    pickup_at: datetime | None = None
    note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_pickup_requirement(self) -> "MarketOrderFarmerValidation":
        if self.action == "validate" and self.pickup_at is None:
            raise ValueError("pickup_at is required when validating an order")
        return self


class MarketOrderOut(BaseModel):
    id: UUID
    market_item_id: UUID
    farmer_user_id: UUID
    customer_user_id: UUID
    farmer_name: str
    customer_name: str
    farmer_phone: str
    customer_phone: str
    item_name_snapshot: str
    unit_label_snapshot: str
    unit_price_snapshot: Decimal
    quantity_ordered: Decimal
    total_price: Decimal
    note: str | None
    status: OrderStatus
    pickup_at: datetime | None
    farmer_response_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketOrderMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1200)


class MarketOrderMessageOut(BaseModel):
    id: UUID
    market_order_id: UUID
    sender_user_id: UUID
    sender_name: str
    sender_role: Literal["farmer", "customer"]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
