from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import secrets
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.models.market_item import FarmerMarketItem
from app.models.market_order import MarketOrder
from app.models.market_order_message import MarketOrderMessage
from app.models.olive_inventory_item import FarmerOliveInventoryItem
from app.models.user import User
from app.schemas.market import MarketItemCreate, MarketItemUpdate, MarketOrderCreate, MarketStoreProfileUpdate


ZERO = Decimal("0.00")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _field_provided(payload: MarketItemUpdate, name: str) -> bool:
    return name in payload.model_fields_set


def _generate_pickup_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _farmer_rating_map(db: Session) -> dict[UUID, tuple[float | None, int]]:
    rows = db.execute(
        select(
            MarketOrder.farmer_user_id,
            func.avg(MarketOrder.market_rating),
            func.count(MarketOrder.market_rating),
        )
        .where(MarketOrder.market_rating.is_not(None))
        .group_by(MarketOrder.farmer_user_id)
    ).all()

    out: dict[UUID, tuple[float | None, int]] = {}
    for farmer_user_id, avg_rating, count_rating in rows:
        out[farmer_user_id] = (float(avg_rating) if avg_rating is not None else None, int(count_rating or 0))
    return out


def _item_rating_map(db: Session) -> dict[UUID, tuple[float | None, int]]:
    rows = db.execute(
        select(
            MarketOrder.market_item_id,
            func.avg(MarketOrder.customer_rating),
            func.count(MarketOrder.customer_rating),
        )
        .where(MarketOrder.customer_rating.is_not(None))
        .group_by(MarketOrder.market_item_id)
    ).all()

    out: dict[UUID, tuple[float | None, int]] = {}
    for market_item_id, avg_rating, count_rating in rows:
        out[market_item_id] = (float(avg_rating) if avg_rating is not None else None, int(count_rating or 0))
    return out


def _item_to_out(
    item: FarmerMarketItem,
    farmer: User | None,
    farmer_rating_avg: float | None = None,
    farmer_rating_count: int = 0,
    product_rating_avg: float | None = None,
    product_rating_count: int = 0,
) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "farmer_name": farmer.full_name if farmer else "Farmer",
        "farmer_store_name": farmer.store_name if farmer else None,
        "farmer_store_banner_url": farmer.store_banner_url if farmer else None,
        "farmer_store_about": farmer.store_about if farmer else None,
        "farmer_store_opening_hours": farmer.store_opening_hours if farmer else None,
        "farmer_rating_avg": farmer_rating_avg,
        "farmer_rating_count": farmer_rating_count,
        "product_rating_avg": product_rating_avg,
        "product_rating_count": product_rating_count,
        "item_name": item.item_name,
        "description": item.description,
        "brand_logo_url": item.brand_logo_url,
        "photo_url": item.photo_url,
        "pickup_location": item.pickup_location,
        "unit_label": item.unit_label,
        "price_per_unit": item.price_per_unit,
        "quantity_available": item.quantity_available,
        "linked_inventory_item_id": item.linked_inventory_item_id,
        "is_active": item.is_active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _order_to_out(order: MarketOrder, farmer: User | None, customer: User | None, include_pickup_code: bool = False) -> dict:
    return {
        "id": order.id,
        "market_item_id": order.market_item_id,
        "farmer_user_id": order.farmer_user_id,
        "customer_user_id": order.customer_user_id,
        "farmer_name": farmer.full_name if farmer else "Farmer",
        "customer_name": customer.full_name if customer else "Customer",
        "farmer_phone": farmer.phone if farmer else "",
        "customer_phone": customer.phone if customer else "",
        "item_name_snapshot": order.item_name_snapshot,
        "unit_label_snapshot": order.unit_label_snapshot,
        "unit_price_snapshot": order.unit_price_snapshot,
        "quantity_ordered": order.quantity_ordered,
        "total_price": order.total_price,
        "note": order.note,
        "status": order.status,
        "pickup_at": order.pickup_at,
        "farmer_response_note": order.farmer_response_note,
        "product_rating": order.customer_rating,
        "product_review": order.customer_review,
        "product_reviewed_at": order.customer_reviewed_at,
        "market_rating": order.market_rating,
        "market_review": order.market_review,
        "market_reviewed_at": order.market_reviewed_at,
        "linked_inventory_item_id": order.linked_inventory_item_id,
        "inventory_reserved_quantity": order.inventory_reserved_quantity,
        "inventory_shortage_alert": order.inventory_shortage_alert,
        "inventory_shortage_note": order.inventory_shortage_note,
        "pickup_code": order.pickup_code if include_pickup_code else None,
        "picked_up_at": order.picked_up_at,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def _message_to_out(message: MarketOrderMessage, sender: User | None) -> dict:
    role = "customer"
    if sender and sender.role == "farmer":
        role = "farmer"
    return {
        "id": message.id,
        "market_order_id": message.market_order_id,
        "sender_user_id": message.sender_user_id,
        "sender_name": sender.full_name if sender else "User",
        "sender_role": role,
        "content": message.content,
        "created_at": message.created_at,
    }


def _is_order_actor(order: MarketOrder, user: User) -> bool:
    return order.farmer_user_id == user.id or order.customer_user_id == user.id


def _store_profile_out(user: User) -> dict:
    return {
        "store_name": user.store_name,
        "store_banner_url": user.store_banner_url,
        "store_about": user.store_about,
        "store_opening_hours": user.store_opening_hours,
    }


def _get_owned_inventory_item(db: Session, farmer_user_id: UUID, inventory_item_id: UUID) -> FarmerOliveInventoryItem | None:
    return db.scalar(
        select(FarmerOliveInventoryItem).where(
            FarmerOliveInventoryItem.id == inventory_item_id,
            FarmerOliveInventoryItem.farmer_user_id == farmer_user_id,
        )
    )


def _reserve_inventory_for_order(db: Session, order: MarketOrder) -> tuple[Decimal, bool, str | None]:
    linked_id = order.linked_inventory_item_id
    requested = _round2(Decimal(str(order.quantity_ordered)))

    if linked_id is None:
        return ZERO, False, None

    inventory_item = _get_owned_inventory_item(db, order.farmer_user_id, linked_id)
    if not inventory_item:
        return ZERO, True, "Linked inventory item was not found. Validate with caution."

    on_hand = _round2(Decimal(str(inventory_item.quantity_on_hand or ZERO)))
    pending = _round2(Decimal(str(inventory_item.quantity_pending or ZERO)))
    reserved = min(on_hand, requested)

    if reserved > ZERO:
        inventory_item.quantity_on_hand = _round2(on_hand - reserved)
        inventory_item.quantity_pending = _round2(pending + reserved)

    shortage = _round2(requested - reserved)
    if shortage > ZERO:
        unit_label = order.unit_label_snapshot
        note = f"Inventory shortage: missing {shortage:.2f} {unit_label}. You can still proceed manually."
        return reserved, True, note

    return reserved, False, None


def _release_inventory_reservation(db: Session, order: MarketOrder) -> None:
    if order.linked_inventory_item_id is None:
        return

    reserved = _round2(Decimal(str(order.inventory_reserved_quantity or ZERO)))
    if reserved <= ZERO:
        return

    inventory_item = _get_owned_inventory_item(db, order.farmer_user_id, order.linked_inventory_item_id)
    if not inventory_item:
        return

    on_hand = _round2(Decimal(str(inventory_item.quantity_on_hand or ZERO)))
    pending = _round2(Decimal(str(inventory_item.quantity_pending or ZERO)))

    inventory_item.quantity_on_hand = _round2(on_hand + reserved)
    inventory_item.quantity_pending = _round2(max(ZERO, pending - reserved))


def _finalize_inventory_pickup(db: Session, order: MarketOrder) -> None:
    if order.linked_inventory_item_id is None:
        return

    reserved = _round2(Decimal(str(order.inventory_reserved_quantity or ZERO)))
    if reserved <= ZERO:
        return

    inventory_item = _get_owned_inventory_item(db, order.farmer_user_id, order.linked_inventory_item_id)
    if not inventory_item:
        return

    pending = _round2(Decimal(str(inventory_item.quantity_pending or ZERO)))
    inventory_item.quantity_pending = _round2(max(ZERO, pending - reserved))


def get_farmer_store_profile(db: Session, farmer_user_id: UUID) -> dict | None:
    farmer = db.get(User, farmer_user_id)
    if not farmer or farmer.role != "farmer":
        return None
    return _store_profile_out(farmer)


def update_farmer_store_profile(db: Session, farmer_user_id: UUID, payload: MarketStoreProfileUpdate) -> dict | None:
    farmer = db.get(User, farmer_user_id)
    if not farmer or farmer.role != "farmer":
        return None

    if "store_name" in payload.model_fields_set:
        farmer.store_name = _clean_optional(payload.store_name)
    if "store_banner_url" in payload.model_fields_set:
        farmer.store_banner_url = _clean_optional(payload.store_banner_url)
    if "store_about" in payload.model_fields_set:
        farmer.store_about = _clean_optional(payload.store_about)
    if "store_opening_hours" in payload.model_fields_set:
        farmer.store_opening_hours = _clean_optional(payload.store_opening_hours)

    db.commit()
    db.refresh(farmer)
    return _store_profile_out(farmer)


def list_active_market_items(db: Session, query: str | None = None) -> list[dict]:
    stmt = (
        select(FarmerMarketItem, User)
        .join(User, User.id == FarmerMarketItem.farmer_user_id)
        .where(
            FarmerMarketItem.is_active.is_(True),
            or_(FarmerMarketItem.quantity_available.is_(None), FarmerMarketItem.quantity_available > 0),
        )
        .order_by(FarmerMarketItem.updated_at.desc())
    )

    if query:
        like_query = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                FarmerMarketItem.item_name.ilike(like_query),
                FarmerMarketItem.description.ilike(like_query),
                FarmerMarketItem.pickup_location.ilike(like_query),
                User.full_name.ilike(like_query),
                User.store_name.ilike(like_query),
                User.store_about.ilike(like_query),
            )
        )

    farmer_ratings = _farmer_rating_map(db)
    item_ratings = _item_rating_map(db)
    rows = db.execute(stmt).all()
    out: list[dict] = []
    for item, farmer in rows:
        farmer_avg, farmer_count = farmer_ratings.get(item.farmer_user_id, (None, 0))
        item_avg, item_count = item_ratings.get(item.id, (None, 0))
        out.append(_item_to_out(item, farmer, farmer_avg, farmer_count, item_avg, item_count))
    return out


def list_farmer_market_items(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerMarketItem)
        .where(FarmerMarketItem.farmer_user_id == farmer_user_id)
        .order_by(FarmerMarketItem.updated_at.desc())
    ).all()

    farmer_ratings = _farmer_rating_map(db)
    item_ratings = _item_rating_map(db)
    farmer = db.get(User, farmer_user_id)
    farmer_avg, farmer_count = farmer_ratings.get(farmer_user_id, (None, 0))
    return [
        _item_to_out(
            item,
            farmer,
            farmer_avg,
            farmer_count,
            item_ratings.get(item.id, (None, 0))[0],
            item_ratings.get(item.id, (None, 0))[1],
        )
        for item in rows
    ]


def create_market_item(db: Session, farmer_user_id: UUID, payload: MarketItemCreate) -> dict:
    linked_inventory_item_id = payload.linked_inventory_item_id
    unit_label = payload.unit_label.strip()

    if linked_inventory_item_id is not None:
        inventory_item = _get_owned_inventory_item(db, farmer_user_id, linked_inventory_item_id)
        if not inventory_item:
            raise ValueError("Linked inventory item not found")
        unit_label = inventory_item.unit_label

    row = FarmerMarketItem(
        farmer_user_id=farmer_user_id,
        item_name=payload.item_name.strip(),
        description=_clean_optional(payload.description),
        brand_logo_url=_clean_optional(payload.brand_logo_url),
        photo_url=_clean_optional(payload.photo_url),
        pickup_location=_clean_optional(payload.pickup_location),
        unit_label=unit_label,
        price_per_unit=payload.price_per_unit,
        quantity_available=payload.quantity_available,
        linked_inventory_item_id=linked_inventory_item_id,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    farmer_ratings = _farmer_rating_map(db)
    farmer = db.get(User, farmer_user_id)
    farmer_avg, farmer_count = farmer_ratings.get(farmer_user_id, (None, 0))
    return _item_to_out(row, farmer, farmer_avg, farmer_count, None, 0)


def update_market_item(db: Session, item_id: UUID, farmer_user_id: UUID, payload: MarketItemUpdate) -> dict | None:
    row = db.get(FarmerMarketItem, item_id)
    if not row or row.farmer_user_id != farmer_user_id:
        return None

    if _field_provided(payload, "linked_inventory_item_id"):
        if payload.linked_inventory_item_id is None:
            row.linked_inventory_item_id = None
        else:
            inventory_item = _get_owned_inventory_item(db, farmer_user_id, payload.linked_inventory_item_id)
            if not inventory_item:
                raise ValueError("Linked inventory item not found")
            row.linked_inventory_item_id = inventory_item.id
            row.unit_label = inventory_item.unit_label

    if _field_provided(payload, "item_name") and payload.item_name is not None:
        row.item_name = payload.item_name.strip()
    if _field_provided(payload, "description"):
        row.description = _clean_optional(payload.description)
    if _field_provided(payload, "brand_logo_url"):
        row.brand_logo_url = _clean_optional(payload.brand_logo_url)
    if _field_provided(payload, "photo_url"):
        row.photo_url = _clean_optional(payload.photo_url)
    if _field_provided(payload, "pickup_location"):
        row.pickup_location = _clean_optional(payload.pickup_location)
    if _field_provided(payload, "unit_label") and payload.unit_label is not None and row.linked_inventory_item_id is None:
        row.unit_label = payload.unit_label.strip()
    if _field_provided(payload, "price_per_unit") and payload.price_per_unit is not None:
        row.price_per_unit = payload.price_per_unit
    if _field_provided(payload, "quantity_available"):
        row.quantity_available = payload.quantity_available
    if _field_provided(payload, "is_active") and payload.is_active is not None:
        row.is_active = payload.is_active

    db.commit()
    db.refresh(row)

    farmer_ratings = _farmer_rating_map(db)
    item_ratings = _item_rating_map(db)
    farmer = db.get(User, farmer_user_id)
    farmer_avg, farmer_count = farmer_ratings.get(farmer_user_id, (None, 0))
    item_avg, item_count = item_ratings.get(row.id, (None, 0))
    return _item_to_out(row, farmer, farmer_avg, farmer_count, item_avg, item_count)


def delete_market_item(db: Session, item_id: UUID, farmer_user_id: UUID) -> bool:
    row = db.get(FarmerMarketItem, item_id)
    if not row or row.farmer_user_id != farmer_user_id:
        return False

    db.delete(row)
    db.commit()
    return True


def create_market_order(db: Session, customer_user_id: UUID, payload: MarketOrderCreate) -> dict:
    item = db.get(FarmerMarketItem, payload.market_item_id)
    if not item or not item.is_active:
        raise ValueError("Market item is not available")

    requested = Decimal(str(payload.quantity_ordered))
    if requested <= 0:
        raise ValueError("Ordered quantity must be positive")

    available = Decimal(str(item.quantity_available)) if item.quantity_available is not None else None
    if available is not None and requested > available:
        raise ValueError("Requested quantity exceeds available stock")

    unit_price = Decimal(str(item.price_per_unit))
    total_price = _round2(unit_price * requested)

    order = MarketOrder(
        market_item_id=item.id,
        farmer_user_id=item.farmer_user_id,
        customer_user_id=customer_user_id,
        item_name_snapshot=item.item_name,
        unit_label_snapshot=item.unit_label,
        unit_price_snapshot=unit_price,
        quantity_ordered=requested,
        total_price=total_price,
        note=payload.note.strip() if payload.note else None,
        linked_inventory_item_id=item.linked_inventory_item_id,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    farmer = db.get(User, order.farmer_user_id)
    customer = db.get(User, order.customer_user_id)
    return _order_to_out(order, farmer, customer, include_pickup_code=True)


def customer_review_market_order(
    db: Session,
    order_id: UUID,
    customer_user_id: UUID,
    product_rating: int | None,
    product_review: str | None,
    market_rating: int | None,
    market_review: str | None,
) -> dict | None:
    order = db.get(MarketOrder, order_id)
    if not order or order.customer_user_id != customer_user_id:
        return None

    if order.status not in {"validated", "picked_up"}:
        raise ValueError("Only validated or picked up orders can be reviewed")

    if product_rating is None and market_rating is None:
        raise ValueError("At least one rating is required")

    now = utcnow_naive()

    if product_rating is not None:
        order.customer_rating = product_rating
        order.customer_review = product_review.strip() if product_review else None
        order.customer_reviewed_at = now

    if market_rating is not None:
        order.market_rating = market_rating
        order.market_review = market_review.strip() if market_review else None
        order.market_reviewed_at = now

    db.commit()
    db.refresh(order)

    farmer = db.get(User, order.farmer_user_id)
    customer = db.get(User, order.customer_user_id)
    return _order_to_out(order, farmer, customer, include_pickup_code=True)


def list_customer_orders(db: Session, customer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(MarketOrder)
        .where(MarketOrder.customer_user_id == customer_user_id)
        .order_by(MarketOrder.created_at.desc())
    ).all()

    out: list[dict] = []
    for order in rows:
        farmer = db.get(User, order.farmer_user_id)
        customer = db.get(User, order.customer_user_id)
        out.append(_order_to_out(order, farmer, customer, include_pickup_code=True))
    return out


def list_farmer_orders(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(MarketOrder)
        .where(MarketOrder.farmer_user_id == farmer_user_id)
        .order_by(MarketOrder.created_at.desc())
    ).all()

    out: list[dict] = []
    for order in rows:
        farmer = db.get(User, order.farmer_user_id)
        customer = db.get(User, order.customer_user_id)
        out.append(_order_to_out(order, farmer, customer, include_pickup_code=False))
    return out


def farmer_validate_market_order(
    db: Session,
    order_id: UUID,
    farmer_user_id: UUID,
    action: str,
    pickup_at,
    note: str | None,
) -> dict | None:
    order = db.get(MarketOrder, order_id)
    if not order or order.farmer_user_id != farmer_user_id:
        return None

    if action == "validate":
        if order.status != "pending":
            raise ValueError("Only pending orders can be validated")
        if pickup_at is None:
            raise ValueError("pickup_at is required when validating an order")

        reserved_qty, shortage_alert, shortage_note = _reserve_inventory_for_order(db, order)
        order.inventory_reserved_quantity = reserved_qty
        order.inventory_shortage_alert = shortage_alert
        order.inventory_shortage_note = shortage_note
        order.status = "validated"
        order.pickup_at = pickup_at
        order.picked_up_at = None
        order.pickup_code = _generate_pickup_code()
        order.farmer_response_note = note.strip() if note else None
    elif action == "reject":
        if order.status != "pending":
            raise ValueError("Only pending orders can be rejected")
        order.status = "rejected"
        order.pickup_at = None
        order.pickup_code = None
        order.picked_up_at = None
        order.farmer_response_note = note.strip() if note else None
    elif action == "cancel":
        if order.status != "validated":
            raise ValueError("Only validated orders can be canceled")
        _release_inventory_reservation(db, order)
        order.status = "canceled"
        order.pickup_code = None
        order.picked_up_at = None
        order.farmer_response_note = note.strip() if note else None
    else:
        raise ValueError("Invalid action")

    db.commit()
    db.refresh(order)

    farmer = db.get(User, order.farmer_user_id)
    customer = db.get(User, order.customer_user_id)
    return _order_to_out(order, farmer, customer, include_pickup_code=False)


def farmer_confirm_market_order_pickup(
    db: Session,
    order_id: UUID,
    farmer_user_id: UUID,
    pickup_code: str,
) -> dict | None:
    order = db.get(MarketOrder, order_id)
    if not order or order.farmer_user_id != farmer_user_id:
        return None

    if order.status != "validated":
        raise ValueError("Only validated orders can be marked as picked up")

    code = (pickup_code or "").strip()
    if not code:
        raise ValueError("Pickup code is required")

    if code != (order.pickup_code or ""):
        raise ValueError("Invalid pickup code")

    _finalize_inventory_pickup(db, order)
    order.status = "picked_up"
    order.picked_up_at = utcnow_naive()

    db.commit()
    db.refresh(order)

    farmer = db.get(User, order.farmer_user_id)
    customer = db.get(User, order.customer_user_id)
    return _order_to_out(order, farmer, customer, include_pickup_code=False)


def _get_order_if_actor(db: Session, order_id: UUID, current_user: User) -> MarketOrder | None:
    order = db.get(MarketOrder, order_id)
    if not order or not _is_order_actor(order, current_user):
        return None
    return order


def list_market_order_messages(db: Session, order_id: UUID, current_user: User) -> list[dict] | None:
    order = _get_order_if_actor(db, order_id, current_user)
    if not order:
        return None

    rows = db.scalars(
        select(MarketOrderMessage)
        .where(MarketOrderMessage.market_order_id == order_id)
        .order_by(MarketOrderMessage.created_at.asc())
    ).all()

    out: list[dict] = []
    for row in rows:
        sender = db.get(User, row.sender_user_id)
        out.append(_message_to_out(row, sender))
    return out


def create_market_order_message(db: Session, order_id: UUID, current_user: User, content: str) -> dict | None:
    order = _get_order_if_actor(db, order_id, current_user)
    if not order:
        return None

    message = MarketOrderMessage(
        market_order_id=order_id,
        sender_user_id=current_user.id,
        content=content.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    sender = db.get(User, message.sender_user_id)
    return _message_to_out(message, sender)
