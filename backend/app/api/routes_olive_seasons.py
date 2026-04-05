from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_season import OliveSeasonCreate, OliveSeasonOut, OliveSeasonTankPriceUpdate, OliveSeasonUpdate
from app.services.olive_seasons import (
    clear_all_olive_season_oil_tank_prices,
    clear_olive_season_oil_tank_price,
    create_olive_season,
    delete_olive_season,
    list_my_olive_seasons,
    update_olive_season,
    update_olive_season_oil_tank_price,
)

router = APIRouter(tags=["Olive Seasons"])


@router.get("/olive-seasons/mine", response_model=list[OliveSeasonOut])
def list_my_olive_seasons_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OliveSeasonOut]:
    rows = list_my_olive_seasons(db, current_user.id)
    return [OliveSeasonOut.model_validate(row) for row in rows]


@router.post("/olive-seasons", response_model=OliveSeasonOut, status_code=status.HTTP_201_CREATED)
def create_olive_season_endpoint(
    payload: OliveSeasonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveSeasonOut:
    try:
        row = create_olive_season(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OliveSeasonOut.model_validate(row)


@router.patch("/olive-seasons/{season_id}", response_model=OliveSeasonOut)
def update_olive_season_endpoint(
    season_id: UUID,
    payload: OliveSeasonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveSeasonOut:
    try:
        row = update_olive_season(db, season_id, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season record not found")
    return OliveSeasonOut.model_validate(row)


@router.patch("/olive-seasons/{season_id}/oil-tank-price", response_model=OliveSeasonOut)
def update_olive_season_oil_tank_price_endpoint(
    season_id: UUID,
    payload: OliveSeasonTankPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveSeasonOut:
    row = update_olive_season_oil_tank_price(db, season_id, current_user.id, payload.unit_price)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season record not found")
    return OliveSeasonOut.model_validate(row)


@router.delete("/olive-seasons/{season_id}/oil-tank-price", response_model=OliveSeasonOut)
def clear_olive_season_oil_tank_price_endpoint(
    season_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveSeasonOut:
    row = clear_olive_season_oil_tank_price(db, season_id, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season record not found")
    return OliveSeasonOut.model_validate(row)


@router.delete("/olive-seasons/oil-tank-prices", status_code=status.HTTP_200_OK)
def clear_all_olive_season_oil_tank_prices_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> dict[str, int]:
    cleared_count = clear_all_olive_season_oil_tank_prices(db, current_user.id)
    return {"cleared_count": cleared_count}


@router.delete("/olive-seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_olive_season_endpoint(
    season_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_olive_season(db, season_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season record not found")
