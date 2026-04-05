from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.olive_inventory_item import FarmerOliveInventoryItem
from app.models.olive_sale import FarmerOliveSale
from app.models.olive_season import FarmerOliveSeason
from app.models.olive_usage import FarmerOliveUsage
from app.schemas.olive_sale import OliveSaleCreate


ZERO = Decimal("0.00")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _kg_needed_per_tank(season: FarmerOliveSeason) -> Decimal | None:
    kg_value = None
    if season.kg_per_land_piece is not None:
        kg_value = Decimal(str(season.kg_per_land_piece))
    elif season.actual_chonbol is not None:
        kg_value = Decimal(str(season.actual_chonbol))

    tanks_value = Decimal(str(season.tanks_20l)) if season.tanks_20l is not None else None
    if kg_value is None or tanks_value is None or tanks_value <= 0:
        return None

    return _round2(kg_value / tanks_value)


def _to_out(item: FarmerOliveSale) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "season_id": item.season_id,
        "sold_on": item.sold_on,
        "sale_type": item.sale_type,
        "tanks_sold": item.tanks_sold,
        "price_per_tank": item.price_per_tank,
        "raw_kg_sold": item.raw_kg_sold,
        "price_per_kg": item.price_per_kg,
        "containers_sold": item.containers_sold,
        "container_size_label": item.container_size_label,
        "kg_per_container": item.kg_per_container,
        "price_per_container": item.price_per_container,
        "custom_inventory_item_id": item.custom_inventory_item_id,
        "custom_item_name": item.custom_item_name,
        "custom_quantity_sold": item.custom_quantity_sold,
        "custom_unit_label": item.custom_unit_label,
        "custom_price_per_unit": item.custom_price_per_unit,
        "inventory_tanks_delta": item.inventory_tanks_delta,
        "total_revenue": item.total_revenue,
        "buyer": item.buyer,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _get_owned_season(db: Session, season_id: UUID, farmer_user_id: UUID) -> FarmerOliveSeason | None:
    return db.scalar(select(FarmerOliveSeason).where(FarmerOliveSeason.id == season_id, FarmerOliveSeason.farmer_user_id == farmer_user_id))


def _get_owned_inventory_item(db: Session, item_id: UUID, farmer_user_id: UUID) -> FarmerOliveInventoryItem | None:
    return db.scalar(select(FarmerOliveInventoryItem).where(FarmerOliveInventoryItem.id == item_id, FarmerOliveInventoryItem.farmer_user_id == farmer_user_id))


def _remaining_tanks_before_new_move(db: Session, season: FarmerOliveSeason, farmer_user_id: UUID) -> Decimal:
    if season.tanks_taken_home_20l is None:
        raise ValueError("Set tanks taken home before recording sales/usage")

    sold_sum = db.scalar(
        select(func.coalesce(func.sum(FarmerOliveSale.inventory_tanks_delta), 0)).where(
            FarmerOliveSale.farmer_user_id == farmer_user_id,
            FarmerOliveSale.season_id == season.id,
        )
    )
    used_sum = db.scalar(
        select(func.coalesce(func.sum(FarmerOliveUsage.tanks_used), 0)).where(
            FarmerOliveUsage.farmer_user_id == farmer_user_id,
            FarmerOliveUsage.season_id == season.id,
        )
    )

    taken_home = _round2(Decimal(str(season.tanks_taken_home_20l)))
    sold = _round2(Decimal(str(sold_sum or ZERO)))
    used = _round2(Decimal(str(used_sum or ZERO)))
    return _round2(taken_home - sold - used)


def list_my_sales(db: Session, farmer_user_id: UUID, season_id: UUID | None = None) -> list[dict]:
    query = select(FarmerOliveSale).where(FarmerOliveSale.farmer_user_id == farmer_user_id)
    if season_id:
        query = query.where(FarmerOliveSale.season_id == season_id)
    rows = db.scalars(query.order_by(FarmerOliveSale.sold_on.desc(), FarmerOliveSale.created_at.desc())).all()
    return [_to_out(row) for row in rows]


def create_sale(db: Session, farmer_user_id: UUID, payload: OliveSaleCreate) -> dict:
    season = _get_owned_season(db, payload.season_id, farmer_user_id)
    if not season:
        raise ValueError("Season record not found")

    sale_type = payload.sale_type
    total_revenue = ZERO
    inventory_tanks_delta = ZERO

    custom_inventory_item = None
    custom_item_name = payload.custom_item_name
    custom_unit_label = payload.custom_unit_label
    custom_price_per_unit = payload.custom_price_per_unit

    if sale_type == "oil_tank":
        tanks_sold = Decimal(str(payload.tanks_sold or ZERO))
        price_per_tank = Decimal(str(payload.price_per_tank or ZERO))
        total_revenue = _round2(tanks_sold * price_per_tank)
        inventory_tanks_delta = _round2(tanks_sold)
    elif sale_type == "raw_kg":
        raw_kg_sold = Decimal(str(payload.raw_kg_sold or ZERO))
        price_per_kg = Decimal(str(payload.price_per_kg or ZERO))
        total_revenue = _round2(raw_kg_sold * price_per_kg)
        inventory_tanks_delta = ZERO
    elif sale_type == "processed_container":
        containers_sold = Decimal(str(payload.containers_sold or ZERO))
        kg_per_container = Decimal(str(payload.kg_per_container or ZERO))
        price_per_container = Decimal(str(payload.price_per_container or ZERO))
        total_revenue = _round2(containers_sold * price_per_container)

        kg_needed = _kg_needed_per_tank(season)
        if kg_needed is None or kg_needed <= 0:
            raise ValueError("Cannot convert processed container sales to inventory tanks. Please fill season KG and Tanks first.")

        total_kg_sold = _round2(containers_sold * kg_per_container)
        inventory_tanks_delta = _round2(total_kg_sold / kg_needed)
    else:
        custom_qty = Decimal(str(payload.custom_quantity_sold or ZERO))
        if payload.custom_inventory_item_id:
            custom_inventory_item = _get_owned_inventory_item(db, payload.custom_inventory_item_id, farmer_user_id)
            if not custom_inventory_item:
                raise ValueError("Inventory item not found")

            on_hand = Decimal(str(custom_inventory_item.quantity_on_hand or ZERO))
            if custom_qty > on_hand:
                raise ValueError("Not enough stock in inventory for this item")

            custom_inventory_item.quantity_on_hand = _round2(on_hand - custom_qty)
            custom_item_name = custom_inventory_item.item_name
            custom_unit_label = custom_inventory_item.unit_label
            if custom_price_per_unit is None:
                custom_price_per_unit = custom_inventory_item.default_price_per_unit

        custom_price = Decimal(str(custom_price_per_unit or ZERO))
        total_revenue = _round2(custom_qty * custom_price)
        inventory_tanks_delta = _round2(Decimal(str(payload.custom_inventory_tanks_delta or ZERO)))

    # Logical guard: you cannot sell more tanks than what is left.
    if inventory_tanks_delta > ZERO:
        remaining_before = _remaining_tanks_before_new_move(db, season, farmer_user_id)
        if inventory_tanks_delta > remaining_before:
            raise ValueError(
                f"Not enough tanks remaining for this sale. Remaining: {remaining_before:.2f}, requested: {inventory_tanks_delta:.2f}"
            )

    item = FarmerOliveSale(
        farmer_user_id=farmer_user_id,
        season_id=payload.season_id,
        sold_on=payload.sold_on,
        sale_type=sale_type,
        tanks_sold=payload.tanks_sold,
        price_per_tank=payload.price_per_tank,
        raw_kg_sold=payload.raw_kg_sold,
        price_per_kg=payload.price_per_kg,
        containers_sold=payload.containers_sold,
        container_size_label=payload.container_size_label,
        kg_per_container=payload.kg_per_container,
        price_per_container=payload.price_per_container,
        custom_inventory_item_id=payload.custom_inventory_item_id,
        custom_item_name=custom_item_name,
        custom_quantity_sold=payload.custom_quantity_sold,
        custom_unit_label=custom_unit_label,
        custom_price_per_unit=custom_price_per_unit,
        inventory_tanks_delta=inventory_tanks_delta,
        total_revenue=total_revenue,
        buyer=payload.buyer,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_sale(db: Session, sale_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveSale, sale_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True
