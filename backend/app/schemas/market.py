from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


OrderStatus = Literal["pending", "validated", "rejected", "canceled", "picked_up"]


class MarketItemBase(BaseModel):
    item_name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    brand_logo_url: str | None = Field(default=None, max_length=500)
    photo_url: str | None = Field(default=None, max_length=500)
    pickup_location: str | None = Field(default=None, max_length=180)
    unit_label: str = Field(min_length=1, max_length=50)
    price_per_unit: Decimal = Field(gt=0)
    quantity_available: Decimal | None = Field(default=None, ge=0)
    linked_inventory_item_id: UUID | None = None
    is_active: bool = True


class MarketItemCreate(MarketItemBase):
    pass


class MarketItemUpdate(BaseModel):
    item_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    brand_logo_url: str | None = Field(default=None, max_length=500)
    photo_url: str | None = Field(default=None, max_length=500)
    pickup_location: str | None = Field(default=None, max_length=180)
    unit_label: str | None = Field(default=None, min_length=1, max_length=50)
    price_per_unit: Decimal | None = Field(default=None, gt=0)
    quantity_available: Decimal | None = Field(default=None, ge=0)
    linked_inventory_item_id: UUID | None = None
    is_active: bool | None = None


class MarketItemOut(BaseModel):
    id: UUID
    farmer_user_id: UUID
    farmer_name: str
    farmer_store_name: str | None
    farmer_store_banner_url: str | None
    farmer_store_about: str | None
    farmer_store_opening_hours: str | None
    farmer_rating_avg: float | None
    farmer_rating_count: int
    product_rating_avg: float | None
    product_rating_count: int
    item_name: str
    description: str | None
    brand_logo_url: str | None
    photo_url: str | None
    pickup_location: str | None
    unit_label: str
    price_per_unit: Decimal
    quantity_available: Decimal | None
    linked_inventory_item_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketStoreProfileOut(BaseModel):
    store_name: str | None
    store_banner_url: str | None
    store_about: str | None
    store_opening_hours: str | None


class MarketStoreProfileUpdate(BaseModel):
    store_name: str | None = Field(default=None, max_length=120)
    store_banner_url: str | None = Field(default=None, max_length=500)
    store_about: str | None = Field(default=None, max_length=600)
    store_opening_hours: str | None = Field(default=None, max_length=180)


class MarketOrderCreate(BaseModel):
    market_item_id: UUID
    quantity_ordered: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=400)


class MarketOrderFarmerValidation(BaseModel):
    action: Literal["validate", "reject", "cancel"]
    pickup_at: datetime | None = None
    note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_pickup_requirement(self) -> "MarketOrderFarmerValidation":
        if self.action == "validate" and self.pickup_at is None:
            raise ValueError("pickup_at is required when validating an order")
        return self


class MarketOrderPickupConfirm(BaseModel):
    pickup_code: str = Field(min_length=4, max_length=12)


class MarketOrderCustomerReview(BaseModel):
    product_rating: int | None = Field(default=None, ge=1, le=5)
    product_review: str | None = Field(default=None, max_length=800)
    market_rating: int | None = Field(default=None, ge=1, le=5)
    market_review: str | None = Field(default=None, max_length=800)

    @model_validator(mode="after")
    def validate_at_least_one_rating(self) -> "MarketOrderCustomerReview":
        if self.product_rating is None and self.market_rating is None:
            raise ValueError("At least one rating is required")
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
    product_rating: int | None
    product_review: str | None
    product_reviewed_at: datetime | None
    market_rating: int | None
    market_review: str | None
    market_reviewed_at: datetime | None
    linked_inventory_item_id: UUID | None
    inventory_reserved_quantity: Decimal
    inventory_shortage_alert: bool
    inventory_shortage_note: str | None
    pickup_code: str | None
    picked_up_at: datetime | None
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
