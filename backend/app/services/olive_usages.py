from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.olive_season import FarmerOliveSeason
from app.models.olive_usage import FarmerOliveUsage
from app.schemas.olive_usage import OliveUsageCreate


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
