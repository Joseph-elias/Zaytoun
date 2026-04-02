from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.olive_land_piece import FarmerOliveLandPiece
from app.models.olive_season import FarmerOliveSeason
from app.schemas.olive_land_piece import OliveLandPieceCreate


def _normalize_piece_name(value: str | None) -> str:
    return " ".join(part for part in str(value or "").strip().split()).casefold()


def _clean_piece_name(value: str | None) -> str:
    cleaned = " ".join(part for part in str(value or "").strip().split())
    if not cleaned:
        raise ValueError("Land piece name is required")
    return cleaned


def _to_out(item: FarmerOliveLandPiece) -> dict:
    return {
        "id": item.id,
        "farmer_user_id": item.farmer_user_id,
        "piece_name": item.piece_name,
        "season_year": item.season_year,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def list_my_land_pieces(db: Session, farmer_user_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(FarmerOliveLandPiece)
        .where(FarmerOliveLandPiece.farmer_user_id == farmer_user_id)
        .order_by(FarmerOliveLandPiece.piece_name.asc(), FarmerOliveLandPiece.created_at.desc())
    ).all()
    return [_to_out(row) for row in rows]


def find_land_piece_by_name(db: Session, farmer_user_id: UUID, piece_name: str) -> FarmerOliveLandPiece | None:
    normalized = _normalize_piece_name(piece_name)
    if not normalized:
        return None

    rows = db.scalars(
        select(FarmerOliveLandPiece).where(FarmerOliveLandPiece.farmer_user_id == farmer_user_id)
    ).all()
    for row in rows:
        if _normalize_piece_name(row.piece_name) == normalized:
            return row
    return None


def ensure_land_piece_exists(db: Session, farmer_user_id: UUID, piece_name: str) -> FarmerOliveLandPiece:
    existing = find_land_piece_by_name(db, farmer_user_id, piece_name)
    if existing:
        return existing

    item = FarmerOliveLandPiece(
        farmer_user_id=farmer_user_id,
        piece_name=_clean_piece_name(piece_name),
        season_year=None,
    )
    db.add(item)
    db.flush()
    return item


def create_land_piece(db: Session, farmer_user_id: UUID, payload: OliveLandPieceCreate) -> dict:
    cleaned_name = _clean_piece_name(payload.piece_name)
    existing = find_land_piece_by_name(db, farmer_user_id, cleaned_name)
    if existing:
        raise ValueError("Land piece already exists")

    item = FarmerOliveLandPiece(
        farmer_user_id=farmer_user_id,
        piece_name=cleaned_name,
        season_year=payload.season_year,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


def delete_land_piece(db: Session, piece_id: UUID, farmer_user_id: UUID) -> bool:
    item = db.get(FarmerOliveLandPiece, piece_id)
    if not item or item.farmer_user_id != farmer_user_id:
        return False

    target_normalized = _normalize_piece_name(item.piece_name)
    seasons = db.scalars(
        select(FarmerOliveSeason).where(FarmerOliveSeason.farmer_user_id == farmer_user_id)
    ).all()
    if any(_normalize_piece_name(season.land_piece_name) == target_normalized for season in seasons):
        raise ValueError("Cannot delete a land piece already used in season data")

    db.delete(item)
    db.commit()
    return True
