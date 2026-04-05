from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.olive_sale import FarmerOliveSale
from app.models.olive_season import FarmerOliveSeason
from app.models.olive_usage import FarmerOliveUsage
from app.schemas.olive_usage import OliveUsageCreate


ZERO = Decimal("0.00")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_out(item: FarmerOliveUsage) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "season_id": item.season_id,
        "used_on": item.used_on,
        "tanks_used": item.tanks_used,
        "usage_type": item.usage_type,
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _get_owned_season(db: Session, season_id: UUID, farmer_user_id: UUID) -> FarmerOliveSeason | None:
    return db.scalar(select(FarmerOliveSeason).where(FarmerOliveSeason.id == season_id, FarmerOliveSeason.farmer_user_id == farmer_user_id))


def _remaining_tanks_before_new_usage(db: Session, season: FarmerOliveSeason, farmer_user_id: UUID) -> Decimal:
    if season.tanks_taken_home_20l is None:
        raise ValueError("Set tanks taken home before recording usage")

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


def list_my_usages(db: Session, farmer_user_id: UUID, season_id: UUID | None = None) -> list[dict]:
    query = select(FarmerOliveUsage).where(FarmerOliveUsage.farmer_user_id == farmer_user_id)
    if season_id:
        query = query.where(FarmerOliveUsage.season_id == season_id)
    rows = db.scalars(query.order_by(FarmerOliveUsage.used_on.desc(), FarmerOliveUsage.created_at.desc())).all()
    return [_to_out(row) for row in rows]


def create_usage(db: Session, farmer_user_id: UUID, payload: OliveUsageCreate) -> dict:
    season = _get_owned_season(db, payload.season_id, farmer_user_id)
    if not season:
        raise ValueError("Season record not found")

    tanks_used = _round2(Decimal(str(payload.tanks_used or ZERO)))
    if tanks_used > ZERO:
        remaining_before = _remaining_tanks_before_new_usage(db, season, farmer_user_id)
        if tanks_used > remaining_before:
            raise ValueError(
                f"Not enough tanks remaining for this usage. Remaining: {remaining_before:.2f}, requested: {tanks_used:.2f}"
            )

    item = FarmerOliveUsage(
        farmer_user_id=farmer_user_id,
        season_id=payload.season_id,
        used_on=payload.used_on,
        tanks_used=payload.tanks_used,
        usage_type=payload.usage_type,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_usage(db: Session, usage_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveUsage, usage_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True
