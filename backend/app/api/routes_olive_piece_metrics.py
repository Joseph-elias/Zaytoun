from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.olive_piece_metric import OlivePieceMetricCreate, OlivePieceMetricOut, OlivePieceMetricUpdate
from app.services.olive_piece_metrics import create_piece_metric, delete_piece_metric, list_my_piece_metrics, update_piece_metric

router = APIRouter(tags=["Olive Piece Metrics"])


@router.get("/olive-piece-metrics/mine", response_model=list[OlivePieceMetricOut])
def list_my_piece_metrics_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[OlivePieceMetricOut]:
    rows = list_my_piece_metrics(db, current_user.id)
    return [OlivePieceMetricOut.model_validate(row) for row in rows]


@router.post("/olive-piece-metrics", response_model=OlivePieceMetricOut, status_code=status.HTTP_201_CREATED)
def create_piece_metric_endpoint(
    payload: OlivePieceMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OlivePieceMetricOut:
    try:
        row = create_piece_metric(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OlivePieceMetricOut.model_validate(row)


@router.patch("/olive-piece-metrics/{metric_id}", response_model=OlivePieceMetricOut)
def update_piece_metric_endpoint(
    metric_id: UUID,
    payload: OlivePieceMetricUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> OlivePieceMetricOut:
    try:
        row = update_piece_metric(db, metric_id, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Piece metric not found")
    return OlivePieceMetricOut.model_validate(row)


@router.delete("/olive-piece-metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_piece_metric_endpoint(
    metric_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> None:
    deleted = delete_piece_metric(db, metric_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Piece metric not found")
