from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.olive_season import FarmerOliveSeason
from app.schemas.olive_season import OliveSeasonCreate, OliveSeasonUpdate


def _kg_needed_per_tank(kg_per_land_piece: Decimal | None, actual_chonbol: Decimal | None, tanks_20l: int | None) -> Decimal | None:
    base_kg = kg_per_land_piece if kg_per_land_piece is not None else actual_chonbol
    if base_kg is None or tanks_20l is None or tanks_20l <= 0:
        return None
    return (base_kg / Decimal(tanks_20l)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_out(item: FarmerOliveSeason) -> dict:
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
        "kg_needed_per_tank": _kg_needed_per_tank(item.kg_per_land_piece, item.actual_chonbol, item.tanks_20l),
        "notes": item.notes,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _normalize_piece_name(value: str | None) -> str:
    return " ".join(part for part in str(value or "").strip().split()).casefold()


def _validate_piece_name(value: str | None) -> str:
    normalized = _normalize_piece_name(value)
    if not normalized:
        raise ValueError("Land piece name is required")
    return normalized


def list_my_olive_seasons(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerOliveSeason)
        .where(FarmerOliveSeason.farmer_user_id == farmer_user_id)
        .order_by(FarmerOliveSeason.season_year.desc(), FarmerOliveSeason.land_piece_name.asc(), FarmerOliveSeason.created_at.desc())
    ).all()
    return [_to_out(row) for row in rows]


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

    item = FarmerOliveSeason(
        farmer_user_id=farmer_user_id,
        season_year=payload.season_year,
        land_pieces=payload.land_pieces,
        land_piece_name=str(payload.land_piece_name).strip(),
        estimated_chonbol=payload.estimated_chonbol,
        actual_chonbol=payload.actual_chonbol,
        kg_per_land_piece=payload.kg_per_land_piece,
        tanks_20l=payload.tanks_20l,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


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

    item.season_year = payload.season_year
    item.land_pieces = payload.land_pieces
    item.land_piece_name = str(payload.land_piece_name).strip()
    item.estimated_chonbol = payload.estimated_chonbol
    item.actual_chonbol = payload.actual_chonbol
    item.kg_per_land_piece = payload.kg_per_land_piece
    item.tanks_20l = payload.tanks_20l
    item.notes = payload.notes

    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_olive_season(db: Session, season_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveSeason, season_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    db.delete(item)
    db.commit()
    return True
