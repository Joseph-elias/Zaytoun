from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.olive_inventory_item import FarmerOliveInventoryItem
from app.schemas.olive_inventory_item import OliveInventoryItemCreate, OliveInventoryItemUpdate


def _to_out(item: FarmerOliveInventoryItem) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "item_name": item.item_name,
        "unit_label": item.unit_label,
        "quantity_on_hand": item.quantity_on_hand,
        "default_price_per_unit": item.default_price_per_unit,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def list_my_inventory_items(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerOliveInventoryItem)
        .where(FarmerOliveInventoryItem.farmer_user_id == farmer_user_id)
        .order_by(FarmerOliveInventoryItem.item_name.asc(), FarmerOliveInventoryItem.created_at.desc())
    ).all()
    return [_to_out(row) for row in rows]


def create_inventory_item(db: Session, farmer_user_id: UUID, payload: OliveInventoryItemCreate) -> dict:
    item = FarmerOliveInventoryItem(
        farmer_user_id=farmer_user_id,
        item_name=payload.item_name.strip(),
        unit_label=payload.unit_label.strip(),
        quantity_on_hand=payload.quantity_on_hand,
        default_price_per_unit=payload.default_price_per_unit,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


def update_inventory_item(db: Session, item_id: UUID, farmer_user_id: UUID, payload: OliveInventoryItemUpdate) -> dict | None:
    item = db.get(FarmerOliveInventoryItem, item_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return None

    if payload.item_name is not None:
        item.item_name = payload.item_name.strip()
    if payload.unit_label is not None:
        item.unit_label = payload.unit_label.strip()
    if payload.quantity_on_hand is not None:
        item.quantity_on_hand = payload.quantity_on_hand
    if payload.default_price_per_unit is not None:
        item.default_price_per_unit = payload.default_price_per_unit
    if payload.notes is not None:
        item.notes = payload.notes

    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_inventory_item(db: Session, item_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveInventoryItem, item_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True
