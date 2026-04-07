from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.olive_inventory_item import FarmerOliveInventoryItem
from app.models.olive_sale import FarmerOliveSale
from app.models.olive_season import FarmerOliveSeason
from app.models.olive_usage import FarmerOliveUsage
from app.schemas.olive_inventory_item import OliveInventoryItemCreate, OliveInventoryItemUpdate


ZERO = Decimal("0.00")
TANKS_OF_LAST_YEAR_NAME = "Tanks of last year"
TANKS_UNIT_LABEL = "tank"


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _current_year() -> int:
    return datetime.utcnow().year


def _to_out(item: FarmerOliveInventoryItem) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "inventory_year": item.inventory_year,
        "item_name": item.item_name,
        "unit_label": item.unit_label,
        "quantity_on_hand": item.quantity_on_hand,
        "quantity_pending": item.quantity_pending,
        "default_price_per_unit": item.default_price_per_unit,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _remaining_tanks_for_year(db: Session, farmer_user_id: UUID, season_year: int) -> Decimal:
    seasons = db.scalars(
        select(FarmerOliveSeason).where(
            FarmerOliveSeason.farmer_user_id == farmer_user_id,
            FarmerOliveSeason.season_year == season_year,
        )
    ).all()

    total = ZERO
    for season in seasons:
        taken_home = _round2(Decimal(str(season.tanks_taken_home_20l or ZERO)))
        if taken_home <= ZERO:
            continue

        sold = _round2(
            Decimal(
                str(
                    db.scalar(
                        select(func.coalesce(func.sum(FarmerOliveSale.inventory_tanks_delta), 0)).where(
                            FarmerOliveSale.farmer_user_id == farmer_user_id,
                            FarmerOliveSale.season_id == season.id,
                        )
                    )
                    or ZERO
                )
            )
        )
        used = _round2(
            Decimal(
                str(
                    db.scalar(
                        select(func.coalesce(func.sum(FarmerOliveUsage.tanks_used), 0)).where(
                            FarmerOliveUsage.farmer_user_id == farmer_user_id,
                            FarmerOliveUsage.season_id == season.id,
                        )
                    )
                    or ZERO
                )
            )
        )

        remaining = _round2(taken_home - sold - used)
        if remaining > ZERO:
            total = _round2(total + remaining)

    return total


def list_my_inventory_items(db: Session, farmer_user_id: UUID, inventory_year: int | None = None) -> list[dict]:
    query = select(FarmerOliveInventoryItem).where(FarmerOliveInventoryItem.farmer_user_id == farmer_user_id)
    if inventory_year is not None:
        query = query.where(FarmerOliveInventoryItem.inventory_year == inventory_year)

    rows = db.scalars(
        query.order_by(
            FarmerOliveInventoryItem.inventory_year.desc(),
            FarmerOliveInventoryItem.item_name.asc(),
            FarmerOliveInventoryItem.created_at.desc(),
        )
    ).all()
    return [_to_out(row) for row in rows]


def create_inventory_item(db: Session, farmer_user_id: UUID, payload: OliveInventoryItemCreate) -> dict:
    item = FarmerOliveInventoryItem(
        farmer_user_id=farmer_user_id,
        inventory_year=payload.inventory_year,
        item_name=payload.item_name.strip(),
        unit_label=payload.unit_label.strip(),
        quantity_on_hand=payload.quantity_on_hand,
        quantity_pending=payload.quantity_pending,
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

    if payload.inventory_year is not None:
        item.inventory_year = payload.inventory_year
    if payload.item_name is not None:
        item.item_name = payload.item_name.strip()
    if payload.unit_label is not None:
        item.unit_label = payload.unit_label.strip()
    if payload.quantity_on_hand is not None:
        item.quantity_on_hand = payload.quantity_on_hand
    if payload.quantity_pending is not None:
        item.quantity_pending = payload.quantity_pending
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


def carry_over_inventory_year(db: Session, farmer_user_id: UUID, from_year: int, to_year: int) -> int:
    if from_year == to_year:
        raise ValueError("Source year and target year must be different")

    source_rows = db.scalars(
        select(FarmerOliveInventoryItem).where(
            FarmerOliveInventoryItem.farmer_user_id == farmer_user_id,
            FarmerOliveInventoryItem.inventory_year == from_year,
        )
    ).all()

    target_rows = db.scalars(
        select(FarmerOliveInventoryItem).where(
            FarmerOliveInventoryItem.farmer_user_id == farmer_user_id,
            FarmerOliveInventoryItem.inventory_year == to_year,
        )
    ).all()

    target_map: dict[tuple[str, str], FarmerOliveInventoryItem] = {}
    for row in target_rows:
        key = (row.item_name.strip().casefold(), row.unit_label.strip().casefold())
        target_map[key] = row

    copied = 0
    for src in source_rows:
        key = (src.item_name.strip().casefold(), src.unit_label.strip().casefold())
        qty = _round2(Decimal(str(src.quantity_on_hand or ZERO)))

        target = target_map.get(key)
        if target is None:
            new_item = FarmerOliveInventoryItem(
                farmer_user_id=farmer_user_id,
                inventory_year=to_year,
                item_name=src.item_name,
                unit_label=src.unit_label,
                quantity_on_hand=qty,
                quantity_pending=ZERO,
                default_price_per_unit=src.default_price_per_unit,
                notes=src.notes,
            )
            db.add(new_item)
            target_map[key] = new_item
        else:
            target.quantity_on_hand = _round2(Decimal(str(target.quantity_on_hand or ZERO)) + qty)
            if target.default_price_per_unit is None:
                target.default_price_per_unit = src.default_price_per_unit
        copied += 1

    remaining_tanks = _remaining_tanks_for_year(db, farmer_user_id, from_year)
    if remaining_tanks > ZERO:
        tanks_key = (TANKS_OF_LAST_YEAR_NAME.casefold(), TANKS_UNIT_LABEL.casefold())
        target_tanks = target_map.get(tanks_key)
        if target_tanks is None:
            db.add(
                FarmerOliveInventoryItem(
                    farmer_user_id=farmer_user_id,
                    inventory_year=to_year,
                    item_name=TANKS_OF_LAST_YEAR_NAME,
                    unit_label=TANKS_UNIT_LABEL,
                    quantity_on_hand=remaining_tanks,
                    quantity_pending=ZERO,
                    default_price_per_unit=None,
                    notes=f"Auto carry-over from {from_year} remaining tanks",
                )
            )
        else:
            target_tanks.quantity_on_hand = _round2(Decimal(str(target_tanks.quantity_on_hand or ZERO)) + remaining_tanks)
        copied += 1

    db.commit()
    return copied
