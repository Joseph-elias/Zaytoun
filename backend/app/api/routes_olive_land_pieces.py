from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_land_piece import OliveLandPieceCreate, OliveLandPieceOut
from app.services.olive_land_pieces import create_land_piece, delete_land_piece, list_my_land_pieces

router = APIRouter(tags=["Olive Land Pieces"])


@router.get("/olive-land-pieces/mine", response_model=list[OliveLandPieceOut])
def list_my_land_pieces_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OliveLandPieceOut]:
    rows = list_my_land_pieces(db, current_user.id)
    return [OliveLandPieceOut.model_validate(row) for row in rows]


@router.post("/olive-land-pieces", response_model=OliveLandPieceOut, status_code=status.HTTP_201_CREATED)
def create_land_piece_endpoint(
    payload: OliveLandPieceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveLandPieceOut:
    try:
        row = create_land_piece(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OliveLandPieceOut.model_validate(row)


@router.delete("/olive-land-pieces/{piece_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_land_piece_endpoint(
    piece_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    try:
        deleted = delete_land_piece(db, piece_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Land piece not found")
