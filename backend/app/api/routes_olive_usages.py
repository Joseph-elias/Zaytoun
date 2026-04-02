from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_usage import OliveUsageCreate, OliveUsageOut
from app.services.olive_usages import create_usage, delete_usage, list_my_usages

router = APIRouter(tags=["Olive Usages"])


@router.get("/olive-usages/mine", response_model=list[OliveUsageOut])
def list_my_usages_endpoint(
    season_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OliveUsageOut]:
    rows = list_my_usages(db, current_user.id, season_id)
    return [OliveUsageOut.model_validate(row) for row in rows]


@router.post("/olive-usages", response_model=OliveUsageOut, status_code=status.HTTP_201_CREATED)
def create_usage_endpoint(
    payload: OliveUsageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveUsageOut:
    try:
        row = create_usage(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OliveUsageOut.model_validate(row)


@router.delete("/olive-usages/{usage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usage_endpoint(
    usage_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_usage(db, usage_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage record not found")
