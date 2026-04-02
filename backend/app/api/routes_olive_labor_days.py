from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_labor_day import OliveLaborDayCreate, OliveLaborDayOut
from app.services.olive_labor_days import create_labor_day, delete_labor_day, list_my_labor_days

router = APIRouter(tags=["Olive Labor Days"])


@router.get("/olive-labor-days/mine", response_model=list[OliveLaborDayOut])
def list_my_labor_days_endpoint(
    season_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OliveLaborDayOut]:
    rows = list_my_labor_days(db, current_user.id, season_id)
    return [OliveLaborDayOut.model_validate(row) for row in rows]


@router.post("/olive-labor-days", response_model=OliveLaborDayOut, status_code=status.HTTP_201_CREATED)
def create_labor_day_endpoint(
    payload: OliveLaborDayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveLaborDayOut:
    try:
        row = create_labor_day(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OliveLaborDayOut.model_validate(row)


@router.delete("/olive-labor-days/{labor_day_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_labor_day_endpoint(
    labor_day_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_labor_day(db, labor_day_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Labor day not found")
