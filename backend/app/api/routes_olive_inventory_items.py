from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_inventory_item import (
    OliveInventoryItemCreate,
    OliveInventoryItemOut,
    OliveInventoryItemUpdate,
)
from app.services.olive_inventory_items import (
    create_inventory_item,
    delete_inventory_item,
    list_my_inventory_items,
    update_inventory_item,
)

router = APIRouter(tags=["Olive Inventory"])


@router.get("/olive-inventory-items/mine", response_model=list[OliveInventoryItemOut])
def list_my_inventory_items_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OliveInventoryItemOut]:
    rows = list_my_inventory_items(db, current_user.id)
    return [OliveInventoryItemOut.model_validate(row) for row in rows]


@router.post("/olive-inventory-items", response_model=OliveInventoryItemOut, status_code=status.HTTP_201_CREATED)
def create_inventory_item_endpoint(
    payload: OliveInventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveInventoryItemOut:
    row = create_inventory_item(db, current_user.id, payload)
    return OliveInventoryItemOut.model_validate(row)


@router.patch("/olive-inventory-items/{item_id}", response_model=OliveInventoryItemOut)
def update_inventory_item_endpoint(
    item_id: UUID,
    payload: OliveInventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OliveInventoryItemOut:
    row = update_inventory_item(db, item_id, current_user.id, payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return OliveInventoryItemOut.model_validate(row)


@router.delete("/olive-inventory-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item_endpoint(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_inventory_item(db, item_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
