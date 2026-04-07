from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.market_item import FarmerMarketItem
from app.models.market_order import MarketOrder
from app.models.market_order_message import MarketOrderMessage
from app.models.user import User
from app.schemas.market import MarketItemCreate, MarketItemUpdate, MarketOrderCreate


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _item_to_out(item: FarmerMarketItem, farmer_name: str) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "farmer_name": farmer_name,
        "item_name": item.item_name,
        "description": item.description,
        "unit_label": item.unit_label,
        "price_per_unit": item.price_per_unit,
        "quantity_available": item.quantity_available,
        "is_active": item.is_active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _order_to_out(order: MarketOrder, farmer: User | None, customer: User | None) -> dict:
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


def list_active_market_items(db: Session, query: str | None = None) -> list[dict]:
    stmt = (
        select(FarmerMarketItem, User.full_name)
        .join(User, User.id == FarmerMarketItem.farmer_user_id)
        .where(FarmerMarketItem.is_active.is_(True), FarmerMarketItem.quantity_available > 0)
        .order_by(FarmerMarketItem.updated_at.desc())
    )

    if query:
        like_query = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                FarmerMarketItem.item_name.ilike(like_query),
                FarmerMarketItem.description.ilike(like_query),
                User.full_name.ilike(like_query),
            )
        )

    rows = db.execute(stmt).all()
    return [_item_to_out(item, farmer_name) for item, farmer_name in rows]


def list_farmer_market_items(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerMarketItem)
        .where(FarmerMarketItem.farmer_user_id == farmer_user_id)
        .order_by(FarmerMarketItem.updated_at.desc())
    ).all()

    farmer = db.get(User, farmer_user_id)
    farmer_name = farmer.full_name if farmer else "Farmer"
    return [_item_to_out(item, farmer_name) for item in rows]


def create_market_item(db: Session, farmer_user_id: UUID, payload: MarketItemCreate) -> dict:
    row = FarmerMarketItem(
        farmer_user_id=farmer_user_id,
        item_name=payload.item_name.strip(),
        description=payload.description.strip() if payload.description else None,
        unit_label=payload.unit_label.strip(),
        price_per_unit=payload.price_per_unit,
        quantity_available=payload.quantity_available,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    farmer = db.get(User, farmer_user_id)
    farmer_name = farmer.full_name if farmer else "Farmer"
    return _item_to_out(row, farmer_name)


def update_market_item(db: Session, item_id: UUID, farmer_user_id: UUID, payload: MarketItemUpdate) -> dict | None:
    row = db.get(FarmerMarketItem, item_id)
    if not row or row.farmer_user_id != farmer_user_id:
        return None

    if payload.item_name is not None:
        row.item_name = payload.item_name.strip()
    if payload.description is not None:
        row.description = payload.description.strip() if payload.description else None
    if payload.unit_label is not None:
        row.unit_label = payload.unit_label.strip()
    if payload.price_per_unit is not None:
        row.price_per_unit = payload.price_per_unit
    if payload.quantity_available is not None:
        row.quantity_available = payload.quantity_available
    if payload.is_active is not None:
        row.is_active = payload.is_active

    db.commit()
    db.refresh(row)

    farmer = db.get(User, farmer_user_id)
    farmer_name = farmer.full_name if farmer else "Farmer"
    return _item_to_out(row, farmer_name)


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

    available = Decimal(str(item.quantity_available))
    requested = Decimal(str(payload.quantity_ordered))
    if requested <= 0:
        raise ValueError("Ordered quantity must be positive")
    if requested > available:
        raise ValueError("Requested quantity exceeds available stock")

    unit_price = Decimal(str(item.price_per_unit))
    total_price = _round2(unit_price * requested)

    item.quantity_available = _round2(available - requested)
    if Decimal(str(item.quantity_available)) == Decimal("0.00"):
        item.is_active = False

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
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    farmer = db.get(User, order.farmer_user_id)
    customer = db.get(User, order.customer_user_id)
    return _order_to_out(order, farmer, customer)


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
        out.append(_order_to_out(order, farmer, customer))
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
        out.append(_order_to_out(order, farmer, customer))
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

    if order.status != "pending":
        raise ValueError("Only pending orders can be validated or rejected")

    if action == "validate":
        if pickup_at is None:
            raise ValueError("pickup_at is required when validating an order")
        order.status = "validated"
        order.pickup_at = pickup_at
        order.farmer_response_note = note.strip() if note else None
    elif action == "reject":
        order.status = "rejected"
        order.pickup_at = None
        order.farmer_response_note = note.strip() if note else None
    else:
        raise ValueError("Invalid action")

    db.commit()
    db.refresh(order)

    farmer = db.get(User, order.farmer_user_id)
    customer = db.get(User, order.customer_user_id)
    return _order_to_out(order, farmer, customer)


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
