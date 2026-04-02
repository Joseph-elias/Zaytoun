from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_sale import OliveSaleCreate, OliveSaleOut
from app.services.olive_sales import create_sale, delete_sale, list_my_sales

router = APIRouter(tags=["Olive Sales"])


@router.get("/olive-sales/mine", response_model=list[OliveSaleOut])
def list_my_sales_endpoint(
    season_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OliveSaleOut]:
    rows = list_my_sales(db, current_user.id, season_id)
    return [OliveSaleOut.model_validate(row) for row in rows]


@router.post("/olive-sales", response_model=OliveSaleOut, status_code=status.HTTP_201_CREATED)
def create_sale_endpoint(
    payload: OliveSaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveSaleOut:
    try:
        row = create_sale(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OliveSaleOut.model_validate(row)


@router.delete("/olive-sales/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale_endpoint(
    sale_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_sale(db, sale_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
