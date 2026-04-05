from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.olive_labor_day import FarmerOliveLaborDay
from app.models.olive_sale import FarmerOliveSale
from app.models.olive_usage import FarmerOliveUsage
from app.models.olive_season import FarmerOliveSeason
from app.schemas.olive_season import OliveSeasonCreate, OliveSeasonUpdate
from app.services.olive_land_pieces import validate_land_piece_for_season


ZERO = Decimal("0.00")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _kg_needed_per_tank(kg_per_land_piece: Decimal | None, actual_chonbol: Decimal | None, tanks_20l: int | None) -> Decimal | None:
    base_kg = kg_per_land_piece if kg_per_land_piece is not None else actual_chonbol
    if base_kg is None or tanks_20l is None or tanks_20l <= 0:
        return None
    return (base_kg / Decimal(tanks_20l)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_piece_name(value: str | None) -> str:
    return " ".join(part for part in str(value or "").strip().split()).casefold()


def _validate_piece_name(value: str | None) -> str:
    normalized = _normalize_piece_name(value)
    if not normalized:
        raise ValueError("Land piece name is required")
    return normalized


def _normalize_tank_values(payload: OliveSeasonCreate | OliveSeasonUpdate) -> tuple[Decimal | None, Decimal, Decimal | None]:
    produced = Decimal(str(payload.tanks_20l)) if payload.tanks_20l is not None else None
    pressing_mode = str(payload.pressing_cost_mode or "money")
    pressing_money = _round2(Decimal(str(payload.pressing_cost))) if payload.pressing_cost is not None else ZERO
    pressing_oil_tanks = _round2(Decimal(str(payload.pressing_cost_oil_tanks_20l))) if payload.pressing_cost_oil_tanks_20l is not None else None
    taken_home = _round2(Decimal(str(payload.tanks_taken_home_20l))) if payload.tanks_taken_home_20l is not None else None

    if pressing_mode == "oil_tanks":
        pressing_money = ZERO

        if produced is None or taken_home is None:
            raise ValueError("For oil_tanks mode, tanks produced and tanks taken home are required")

        if taken_home > produced:
            raise ValueError("Tanks taken home cannot exceed tanks produced")

        pressing_oil_tanks = _round2(produced - taken_home)
        pressing_money = pressing_oil_tanks
    else:
        pressing_oil_tanks = None
        if produced is not None and taken_home is None:
            taken_home = _round2(produced)
        if produced is not None and taken_home is not None and taken_home > produced:
            raise ValueError("Tanks taken home cannot exceed tanks produced")

    return taken_home, pressing_money, pressing_oil_tanks


def _build_financial_maps(db: Session, farmer_user_id: UUID) -> tuple[dict, dict, dict]:
    labor_rows = db.execute(
        select(
            FarmerOliveLaborDay.season_id,
            func.coalesce(func.sum(FarmerOliveLaborDay.men_count * FarmerOliveLaborDay.men_rate + FarmerOliveLaborDay.women_count * FarmerOliveLaborDay.women_rate), 0),
            func.count(FarmerOliveLaborDay.id),
            func.coalesce(func.sum(FarmerOliveLaborDay.men_count + FarmerOliveLaborDay.women_count), 0),
        )
        .where(FarmerOliveLaborDay.farmer_user_id == farmer_user_id)
        .group_by(FarmerOliveLaborDay.season_id)
    ).all()

    sales_rows = db.execute(
        select(
            FarmerOliveSale.season_id,
            func.coalesce(func.sum(FarmerOliveSale.inventory_tanks_delta), 0),
            func.coalesce(func.sum(FarmerOliveSale.total_revenue), 0),
        )
        .where(FarmerOliveSale.farmer_user_id == farmer_user_id)
        .group_by(FarmerOliveSale.season_id)
    ).all()

    usage_rows = db.execute(
        select(
            FarmerOliveUsage.season_id,
            func.coalesce(func.sum(FarmerOliveUsage.tanks_used), 0),
        )
        .where(FarmerOliveUsage.farmer_user_id == farmer_user_id)
        .group_by(FarmerOliveUsage.season_id)
    ).all()

    labor_map = {
        row[0]: {
            "labor_cost_total": _round2(Decimal(str(row[1]))),
            "harvest_days": int(row[2] or 0),
            "worker_days": int(row[3] or 0),
        }
        for row in labor_rows
    }

    sales_map = {
        row[0]: {
            "sold_tanks": _round2(Decimal(str(row[1]))),
            "sales_revenue_total": _round2(Decimal(str(row[2]))),
        }
        for row in sales_rows
    }

    usage_map = {
        row[0]: {
            "used_tanks": _round2(Decimal(str(row[1]))),
        }
        for row in usage_rows
    }

    return labor_map, sales_map, usage_map


def _to_out(item: FarmerOliveSeason, labor_map: dict, sales_map: dict, usage_map: dict) -> dict:
    pressing_cost = _round2(Decimal(str(item.pressing_cost))) if item.pressing_cost is not None else ZERO

    labor_info = labor_map.get(item.id, {"labor_cost_total": ZERO, "harvest_days": 0, "worker_days": 0})
    sales_info = sales_map.get(item.id, {"sold_tanks": ZERO, "sales_revenue_total": ZERO})
    usage_info = usage_map.get(item.id, {"used_tanks": ZERO})

    labor_cost_total = labor_info["labor_cost_total"]
    total_cost = _round2(pressing_cost + labor_cost_total)
    sold_tanks = sales_info["sold_tanks"]
    sales_revenue_total = sales_info["sales_revenue_total"]
    used_tanks = usage_info["used_tanks"]
    profit = _round2(sales_revenue_total - total_cost)

    remaining_tanks = None
    if item.tanks_taken_home_20l is not None:
        remaining_tanks = _round2(Decimal(str(item.tanks_taken_home_20l)) - sold_tanks - used_tanks)

    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "season_year": item.season_year,
        "land_pieces": item.land_pieces,
        "land_piece_name": item.land_piece_name,
        "estimated_chonbol": item.estimated_chonbol,
        "actual_chonbol": item.actual_chonbol,
        "kg_per_land_piece": item.kg_per_land_piece,
        "tanks_20l": item.tanks_20l,
        "tanks_taken_home_20l": item.tanks_taken_home_20l,
        "kg_needed_per_tank": _kg_needed_per_tank(item.kg_per_land_piece, item.actual_chonbol, item.tanks_20l),
        "pressing_cost_mode": item.pressing_cost_mode,
        "pressing_cost": _round2(Decimal(str(item.pressing_cost))) if item.pressing_cost is not None else ZERO,
        "pressing_cost_oil_tanks_20l": _round2(Decimal(str(item.pressing_cost_oil_tanks_20l))) if item.pressing_cost_oil_tanks_20l is not None else None,
        "labor_cost_total": labor_cost_total,
        "total_cost": total_cost,
        "sold_tanks": sold_tanks,
        "used_tanks": used_tanks,
        "sales_revenue_total": sales_revenue_total,
        "profit": profit,
        "remaining_tanks": remaining_tanks,
        "harvest_days": labor_info["harvest_days"],
        "worker_days": labor_info["worker_days"],
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def list_my_olive_seasons(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerOliveSeason)
        .where(FarmerOliveSeason.farmer_user_id == farmer_user_id)
        .order_by(FarmerOliveSeason.season_year.desc(), FarmerOliveSeason.land_piece_name.asc(), FarmerOliveSeason.created_at.desc())
    ).all()

    labor_map, sales_map, usage_map = _build_financial_maps(db, farmer_user_id)
    return [_to_out(row, labor_map, sales_map, usage_map) for row in rows]


def create_olive_season(db: Session, farmer_user_id: UUID, payload: OliveSeasonCreate) -> dict:
    incoming_piece = _validate_piece_name(payload.land_piece_name)
    same_year_rows = db.scalars(
        select(FarmerOliveSeason).where(
            FarmerOliveSeason.farmer_user_id == farmer_user_id,
            FarmerOliveSeason.season_year == payload.season_year,
        )
    ).all()
    if any(_normalize_piece_name(row.land_piece_name) == incoming_piece for row in same_year_rows):
        raise ValueError("Season already exists for this year and land piece")

    validate_land_piece_for_season(db, farmer_user_id, str(payload.land_piece_name), payload.season_year)

    tanks_taken_home_20l, pressing_cost, pressing_cost_oil_tanks_20l = _normalize_tank_values(payload)

    item = FarmerOliveSeason(
        farmer_user_id=farmer_user_id,
        season_year=payload.season_year,
        land_pieces=payload.land_pieces,
        land_piece_name=str(payload.land_piece_name).strip(),
        estimated_chonbol=payload.estimated_chonbol,
        actual_chonbol=payload.actual_chonbol,
        kg_per_land_piece=payload.kg_per_land_piece,
        tanks_20l=payload.tanks_20l,
        tanks_taken_home_20l=tanks_taken_home_20l,
        pressing_cost_mode=payload.pressing_cost_mode,
        pressing_cost=pressing_cost,
        pressing_cost_oil_tanks_20l=pressing_cost_oil_tanks_20l,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item, {}, {}, {})


def update_olive_season(db: Session, season_id: UUID, farmer_user_id: UUID, payload: OliveSeasonUpdate) -> dict | None:
    item = db.get(FarmerOliveSeason, season_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return None

    incoming_piece = _validate_piece_name(payload.land_piece_name)
    same_year_rows = db.scalars(
        select(FarmerOliveSeason).where(
            FarmerOliveSeason.id != item.id,
            FarmerOliveSeason.farmer_user_id == farmer_user_id,
            FarmerOliveSeason.season_year == payload.season_year,
        )
    ).all()
    if any(_normalize_piece_name(row.land_piece_name) == incoming_piece for row in same_year_rows):
        raise ValueError("Another season already exists for this year and land piece")

    validate_land_piece_for_season(db, farmer_user_id, str(payload.land_piece_name), payload.season_year)

    tanks_taken_home_20l, pressing_cost, pressing_cost_oil_tanks_20l = _normalize_tank_values(payload)

    item.season_year = payload.season_year
    item.land_pieces = payload.land_pieces
    item.land_piece_name = str(payload.land_piece_name).strip()
    item.estimated_chonbol = payload.estimated_chonbol
    item.actual_chonbol = payload.actual_chonbol
    item.kg_per_land_piece = payload.kg_per_land_piece
    item.tanks_20l = payload.tanks_20l
    item.tanks_taken_home_20l = tanks_taken_home_20l
    item.pressing_cost_mode = payload.pressing_cost_mode
    item.pressing_cost = pressing_cost
    item.pressing_cost_oil_tanks_20l = pressing_cost_oil_tanks_20l
    item.notes = payload.notes

    db.commit()
    db.refresh(item)

    labor_map, sales_map, usage_map = _build_financial_maps(db, farmer_user_id)
    return _to_out(item, labor_map, sales_map, usage_map)


def delete_olive_season(db: Session, season_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveSeason, season_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True



