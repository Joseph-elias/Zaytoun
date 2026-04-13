from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.worker import Worker
from app.schemas.booking import (
    BookingCreate,
    BookingEventOut,
    BookingMessageCreate,
    BookingMessageOut,
    BookingOut,
    BookingProposalUpdate,
    BookingStatus,
    FarmerBookingValidation,
    WorkerBookingResponse,
)
from app.schemas.worker import WorkerAvailabilityUpdate, WorkerCreate, WorkerOut, WorkerUpdate
from app.services.bookings import (
    create_booking_message,
    create_bookings_for_worker,
    delete_booking_proposal,
    farmer_validate_booking,
    list_booking_events,
    list_booking_messages,
    list_farmer_bookings,
    list_worker_received_bookings,
    update_booking_proposal,
    worker_respond_to_booking,
)
from app.services.workers import create_worker, delete_worker, list_workers, update_worker_availability, update_worker_profile

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


@router.patch("/workers/{worker_id}", response_model=WorkerOut)
def update_worker_endpoint(
    worker_id: UUID,
    payload: WorkerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker")),
) -> WorkerOut:
    worker = update_worker_profile(db, worker_id, payload, owner_phone=current_user.phone)
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
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
    work_date: date | None = Query(default=None),
    work_slot: Literal["full_day", "extra_time"] | None = Query(default=None),
    near_latitude: float | None = Query(default=None, ge=-90, le=90),
    near_longitude: float | None = Query(default=None, ge=-180, le=180),
    max_distance_km: float | None = Query(default=None, gt=0),
    sort_by: Literal["newest", "distance"] | None = Query(default=None),
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
        work_date=work_date,
        work_slot=work_slot,
        near_latitude=near_latitude,
        near_longitude=near_longitude,
        max_distance_km=max_distance_km,
        sort_by=sort_by,
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


@router.delete("/workers/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worker_endpoint(
    worker_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker")),
) -> None:
    deleted = delete_worker(db, worker_id, owner_phone=current_user.phone)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")


@router.post("/workers/{worker_id}/bookings", response_model=list[BookingOut], status_code=status.HTTP_201_CREATED)
def create_worker_booking_endpoint(
    worker_id: UUID,
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[BookingOut]:
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    try:
        created = create_bookings_for_worker(db, worker, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return [BookingOut.model_validate(item) for item in created]


@router.get("/bookings/mine", response_model=list[BookingOut])
def list_my_bookings_endpoint(
    status: BookingStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> list[BookingOut]:
    rows = list_farmer_bookings(db, current_user.id, status=status)
    return [BookingOut.model_validate(item) for item in rows]


@router.get("/bookings/received", response_model=list[BookingOut])
def list_received_bookings_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker")),
) -> list[BookingOut]:
    rows = list_worker_received_bookings(db, current_user.phone)
    return [BookingOut.model_validate(item) for item in rows]


@router.patch("/bookings/{booking_id}/worker-response", response_model=BookingOut)
def worker_response_endpoint(
    booking_id: UUID,
    payload: WorkerBookingResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker")),
) -> BookingOut:
    try:
        row = worker_respond_to_booking(db, booking_id, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingOut.model_validate(row)


@router.patch("/bookings/{booking_id}/farmer-validation", response_model=BookingOut)
def farmer_validation_endpoint(
    booking_id: UUID,
    payload: FarmerBookingValidation,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("farmer")),
) -> BookingOut:
    try:
        row = farmer_validate_booking(db, booking_id, current_user, payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingOut.model_validate(row)


@router.patch("/bookings/{booking_id}/proposal", response_model=BookingOut)
def update_booking_proposal_endpoint(
    booking_id: UUID,
    payload: BookingProposalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker", "farmer")),
) -> BookingOut:
    try:
        row = update_booking_proposal(db, booking_id, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingOut.model_validate(row)


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking_endpoint(
    booking_id: UUID,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker", "farmer")),
) -> None:
    try:
        deleted = delete_booking_proposal(db, booking_id, current_user, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")


@router.get("/bookings/{booking_id}/messages", response_model=list[BookingMessageOut])
def list_booking_messages_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker", "farmer")),
) -> list[BookingMessageOut]:
    rows = list_booking_messages(db, booking_id, current_user)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return [BookingMessageOut.model_validate(item) for item in rows]


@router.post("/bookings/{booking_id}/messages", response_model=BookingMessageOut, status_code=status.HTTP_201_CREATED)
def create_booking_message_endpoint(
    booking_id: UUID,
    payload: BookingMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker", "farmer")),
) -> BookingMessageOut:
    item = create_booking_message(db, booking_id, current_user, payload.content)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingMessageOut.model_validate(item)


@router.get("/bookings/{booking_id}/events", response_model=list[BookingEventOut])
def list_booking_events_endpoint(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("worker", "farmer")),
) -> list[BookingEventOut]:
    rows = list_booking_events(db, booking_id, current_user)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return [BookingEventOut.model_validate(item) for item in rows]



