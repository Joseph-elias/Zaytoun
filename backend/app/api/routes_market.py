from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.market import (
    MarketItemCreate,
    MarketItemOut,
    MarketItemUpdate,
    MarketOrderCreate,
    MarketOrderCustomerReview,
    MarketOrderFarmerValidation,
    MarketOrderMessageCreate,
    MarketOrderMessageOut,
    MarketOrderOut,
    MarketStoreProfileOut,
    MarketStoreProfileUpdate,
)
from app.services.market import (
    create_market_item,
    create_market_order,
    create_market_order_message,
    customer_review_market_order,
    delete_market_item,
    farmer_validate_market_order,
    get_farmer_store_profile,
    list_active_market_items,
    list_customer_orders,
    list_farmer_market_items,
    list_farmer_orders,
    list_market_order_messages,
    update_farmer_store_profile,
    update_market_item,
)

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/items", response_model=list[MarketItemOut])
def list_market_items_endpoint(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer", "customer")),
) -> list[MarketItemOut]:
    rows = list_active_market_items(db, query=q)
    return [MarketItemOut.model_validate(row) for row in rows]


@router.get("/items/mine", response_model=list[MarketItemOut])
def list_my_market_items_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[MarketItemOut]:
    rows = list_farmer_market_items(db, current_user.id)
    return [MarketItemOut.model_validate(row) for row in rows]


@router.post("/items", response_model=MarketItemOut, status_code=status.HTTP_201_CREATED)
def create_market_item_endpoint(
    payload: MarketItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> MarketItemOut:
    row = create_market_item(db, current_user.id, payload)
    return MarketItemOut.model_validate(row)


@router.patch("/items/{item_id}", response_model=MarketItemOut)
def update_market_item_endpoint(
    item_id: UUID,
    payload: MarketItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> MarketItemOut:
    row = update_market_item(db, item_id, current_user.id, payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market item not found")
    return MarketItemOut.model_validate(row)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_market_item_endpoint(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_market_item(db, item_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market item not found")


@router.get("/store-profile/mine", response_model=MarketStoreProfileOut)
def get_my_store_profile_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> MarketStoreProfileOut:
    row = get_farmer_store_profile(db, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")
    return MarketStoreProfileOut.model_validate(row)


@router.patch("/store-profile/mine", response_model=MarketStoreProfileOut)
def update_my_store_profile_endpoint(
    payload: MarketStoreProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> MarketStoreProfileOut:
    row = update_farmer_store_profile(db, current_user.id, payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")
    return MarketStoreProfileOut.model_validate(row)


@router.post("/orders", response_model=MarketOrderOut, status_code=status.HTTP_201_CREATED)
def create_market_order_endpoint(
    payload: MarketOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
) -> MarketOrderOut:
    try:
        row = create_market_order(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MarketOrderOut.model_validate(row)


@router.patch("/orders/{order_id}/customer-review", response_model=MarketOrderOut)
def customer_review_market_order_endpoint(
    order_id: UUID,
    payload: MarketOrderCustomerReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
) -> MarketOrderOut:
    try:
        row = customer_review_market_order(
            db,
            order_id=order_id,
            customer_user_id=current_user.id,
            rating=payload.rating,
            review=payload.review,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market order not found")
    return MarketOrderOut.model_validate(row)


@router.patch("/orders/{order_id}/farmer-validation", response_model=MarketOrderOut)
def farmer_validate_market_order_endpoint(
    order_id: UUID,
    payload: MarketOrderFarmerValidation,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> MarketOrderOut:
    try:
        row = farmer_validate_market_order(
            db,
            order_id=order_id,
            farmer_user_id=current_user.id,
            action=payload.action,
            pickup_at=payload.pickup_at,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market order not found")
    return MarketOrderOut.model_validate(row)


@router.get("/orders/mine", response_model=list[MarketOrderOut])
def list_my_market_orders_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("customer")),
) -> list[MarketOrderOut]:
    rows = list_customer_orders(db, current_user.id)
    return [MarketOrderOut.model_validate(row) for row in rows]


@router.get("/orders/incoming", response_model=list[MarketOrderOut])
def list_incoming_market_orders_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[MarketOrderOut]:
    rows = list_farmer_orders(db, current_user.id)
    return [MarketOrderOut.model_validate(row) for row in rows]


@router.get("/orders/{order_id}/messages", response_model=list[MarketOrderMessageOut])
def list_market_order_messages_endpoint(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer", "customer")),
) -> list[MarketOrderMessageOut]:
    rows = list_market_order_messages(db, order_id, current_user)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market order not found")
    return [MarketOrderMessageOut.model_validate(row) for row in rows]


@router.post("/orders/{order_id}/messages", response_model=MarketOrderMessageOut, status_code=status.HTTP_201_CREATED)
def create_market_order_message_endpoint(
    order_id: UUID,
    payload: MarketOrderMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer", "customer")),
) -> MarketOrderMessageOut:
    row = create_market_order_message(db, order_id, current_user, payload.content)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market order not found")
    return MarketOrderMessageOut.model_validate(row)
