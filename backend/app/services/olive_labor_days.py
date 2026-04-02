from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.olive_labor_day import FarmerOliveLaborDay
from app.models.olive_season import FarmerOliveSeason
from app.schemas.olive_labor_day import OliveLaborDayCreate


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _day_total(men_count: int, women_count: int, men_rate: Decimal, women_rate: Decimal) -> Decimal:
    total = Decimal(men_count) * men_rate + Decimal(women_count) * women_rate
    return _round2(total)


def _to_out(item: FarmerOliveLaborDay) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "season_id": item.season_id,
        "work_date": item.work_date,
        "men_count": item.men_count,
        "women_count": item.women_count,
        "men_rate": item.men_rate,
        "women_rate": item.women_rate,
        "total_day_cost": _day_total(item.men_count, item.women_count, item.men_rate, item.women_rate),
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _get_owned_season(db: Session, season_id: UUID, farmer_user_id: UUID) -> FarmerOliveSeason | None:
    return db.scalar(select(FarmerOliveSeason).where(FarmerOliveSeason.id == season_id, FarmerOliveSeason.farmer_user_id == farmer_user_id))


def list_my_labor_days(db: Session, farmer_user_id: UUID, season_id: UUID | None = None) -> list[dict]:
    query = select(FarmerOliveLaborDay).where(FarmerOliveLaborDay.farmer_user_id == farmer_user_id)
    if season_id:
        query = query.where(FarmerOliveLaborDay.season_id == season_id)
    rows = db.scalars(query.order_by(FarmerOliveLaborDay.work_date.desc(), FarmerOliveLaborDay.created_at.desc())).all()
    return [_to_out(row) for row in rows]


def create_labor_day(db: Session, farmer_user_id: UUID, payload: OliveLaborDayCreate) -> dict:
    season = _get_owned_season(db, payload.season_id, farmer_user_id)
    if not season:
        raise ValueError("Season record not found")

    exists = db.scalar(
        select(FarmerOliveLaborDay).where(
            FarmerOliveLaborDay.farmer_user_id == farmer_user_id,
            FarmerOliveLaborDay.season_id == payload.season_id,
            FarmerOliveLaborDay.work_date == payload.work_date,
        )
    )
    if exists:
        raise ValueError("Labor day already exists for this date")

    item = FarmerOliveLaborDay(
        farmer_user_id=farmer_user_id,
        season_id=payload.season_id,
        work_date=payload.work_date,
        men_count=payload.men_count,
        women_count=payload.women_count,
        men_rate=payload.men_rate,
        women_rate=payload.women_rate,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_labor_day(db: Session, labor_day_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveLaborDay, labor_day_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True
