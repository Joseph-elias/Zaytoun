from uuid import UUID

from app.api.dependencies import get_current_user, require_roles
from app.models.user import User
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.worker import WorkerAvailabilityUpdate, WorkerCreate, WorkerOut
from app.services.workers import create_worker, list_workers, update_worker_availability

router = APIRouter(tags=["Workers"])


@router.post("/workers", response_model=WorkerOut, status_code=status.HTTP_201_CREATED)
def create_worker_endpoint(
    payload: WorkerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker")),
) -> WorkerOut:
    if payload.phone != current_user.phone:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker can only create profiles using their own account phone",
        )

    worker = create_worker(db, payload)
    return WorkerOut.model_validate(worker)


@router.get("/workers", response_model=list[WorkerOut])
def list_workers_endpoint(
    available: bool | None = Query(default=None),
    village: str | None = Query(default=None),
    rate_type: Literal["day", "hour"] | None = Query(default=None),
    min_men_rate: Decimal | None = Query(default=None, gt=0),
    max_men_rate: Decimal | None = Query(default=None, gt=0),
    min_women_rate: Decimal | None = Query(default=None, gt=0),
    max_women_rate: Decimal | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkerOut]:
    phone_scope = current_user.phone if current_user.role == "worker" else None

    workers = list_workers(
        db,
        available=available,
        village=village,
        rate_type=rate_type,
        min_men_rate=min_men_rate,
        max_men_rate=max_men_rate,
        min_women_rate=min_women_rate,
        max_women_rate=max_women_rate,
        phone=phone_scope,
    )
    return [WorkerOut.model_validate(worker) for worker in workers]


@router.patch("/workers/{worker_id}/availability", response_model=WorkerOut)
def update_worker_availability_endpoint(
    worker_id: UUID,
    payload: WorkerAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker")),
) -> WorkerOut:
    worker = update_worker_availability(db, worker_id, payload, owner_phone=current_user.phone)
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    return WorkerOut.model_validate(worker)
