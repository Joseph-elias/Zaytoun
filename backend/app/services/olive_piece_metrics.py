from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.olive_piece_metric import FarmerOlivePieceMetric
from app.schemas.olive_piece_metric import OlivePieceMetricCreate, OlivePieceMetricUpdate


def _kg_needed_per_tank(harvested_kg: Decimal | None, tanks_20l: int | None) -> Decimal | None:
    if harvested_kg is None or tanks_20l is None or tanks_20l <= 0:
        return None
    return (harvested_kg / Decimal(tanks_20l)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_out(item: FarmerOlivePieceMetric) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "season_year": item.season_year,
        "piece_label": item.piece_label,
        "harvested_kg": item.harvested_kg,
        "tanks_20l": item.tanks_20l,
        "kg_needed_per_tank": _kg_needed_per_tank(item.harvested_kg, item.tanks_20l),
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def list_my_piece_metrics(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerOlivePieceMetric)
        .where(FarmerOlivePieceMetric.farmer_user_id == farmer_user_id)
        .order_by(FarmerOlivePieceMetric.season_year.desc(), FarmerOlivePieceMetric.piece_label.asc())
    ).all()
    return [_to_out(row) for row in rows]


def create_piece_metric(db: Session, farmer_user_id: UUID, payload: OlivePieceMetricCreate) -> dict:
    existing = db.scalar(
        select(FarmerOlivePieceMetric).where(
            FarmerOlivePieceMetric.farmer_user_id == farmer_user_id,
            FarmerOlivePieceMetric.season_year == payload.season_year,
            FarmerOlivePieceMetric.piece_label == payload.piece_label,
        )
    )
    if existing:
        raise ValueError("Piece metric already exists for this year")

    item = FarmerOlivePieceMetric(
        farmer_user_id=farmer_user_id,
        season_year=payload.season_year,
        piece_label=payload.piece_label,
        harvested_kg=payload.harvested_kg,
        tanks_20l=payload.tanks_20l,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


def update_piece_metric(db: Session, metric_id: UUID, farmer_user_id: UUID, payload: OlivePieceMetricUpdate) -> dict | None:
    item = db.get(FarmerOlivePieceMetric, metric_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return None

    existing = db.scalar(
        select(FarmerOlivePieceMetric).where(
            FarmerOlivePieceMetric.id != item.id,
            FarmerOlivePieceMetric.farmer_user_id == farmer_user_id,
            FarmerOlivePieceMetric.season_year == payload.season_year,
            FarmerOlivePieceMetric.piece_label == payload.piece_label,
        )
    )
    if existing:
        raise ValueError("Another piece metric already exists for this year and piece")

    item.season_year = payload.season_year
    item.piece_label = payload.piece_label
    item.harvested_kg = payload.harvested_kg
    item.tanks_20l = payload.tanks_20l
    item.notes = payload.notes

    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_piece_metric(db: Session, metric_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOlivePieceMetric, metric_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True
