from collections.abc import Sequence
from datetime import date
from decimal import Decimal
import math
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.booking import Booking
from app.models.booking_event import BookingEvent
from app.models.booking_message import BookingMessage
from app.models.worker import Worker
from app.models.worker_availability_slot import WorkerAvailabilitySlot
from app.schemas.worker import (
    WorkSlotType,
    WorkerAvailabilityUpdate,
    WorkerCreate,
    WorkerUpdate,
)
from app.services.capacity import remaining_capacity_for_slot, weekday_name


def _dates_to_storage(dates: list[date]) -> str:
    iso_dates = sorted({value.isoformat() for value in dates})
    return "," + ",".join(iso_dates) + ","


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _normalized_windows(
    available_dates: list[date],
    availability_windows: list,
) -> list[tuple[date, WorkSlotType]]:
    windows: set[tuple[date, WorkSlotType]] = set()
    for item in available_dates:
        windows.add((item, "full_day"))
    for item in availability_windows:
        windows.add((item.work_date, item.slot_type))
    return sorted(windows, key=lambda row: (row[0], row[1]))


def _sync_worker_slots(db: Session, worker: Worker, windows: list[tuple[date, WorkSlotType]]) -> None:
    db.execute(delete(WorkerAvailabilitySlot).where(WorkerAvailabilitySlot.worker_id == worker.id))
    for work_date, slot_type in windows:
        db.add(
            WorkerAvailabilitySlot(
                worker_id=worker.id,
                work_date=work_date,
                slot_type=slot_type,
            )
        )


def _full_day_dates_from_windows(windows: list[tuple[date, WorkSlotType]]) -> list[date]:
    return sorted({work_date for work_date, slot in windows if slot == "full_day"})


def create_worker(db: Session, payload: WorkerCreate) -> Worker:
    data = payload.model_dump(exclude={"availability_windows"})
    windows = _normalized_windows(payload.available_dates, payload.availability_windows)
    data["available_dates"] = _dates_to_storage(_full_day_dates_from_windows(windows))

    worker = Worker(**data)
    db.add(worker)
    db.flush()
    _sync_worker_slots(db, worker, windows)
    db.commit()
    db.refresh(worker)
    return worker


def list_workers(
    db: Session,
    available: bool | None = None,
    village: str | None = None,
    rate_type: str | None = None,
    min_men_rate: Decimal | None = None,
    max_men_rate: Decimal | None = None,
    min_women_rate: Decimal | None = None,
    max_women_rate: Decimal | None = None,
    phone: str | None = None,
    work_date: date | None = None,
    work_slot: WorkSlotType | None = None,
    near_latitude: float | None = None,
    near_longitude: float | None = None,
    max_distance_km: float | None = None,
    sort_by: str | None = None,
) -> Sequence[Worker]:
    query = select(Worker).options(selectinload(Worker.availability_slots))

    if phone:
        query = query.where(Worker.phone == phone)

    if available is not None:
        query = query.where(Worker.available == available)

    if village:
        query = query.where(Worker.village == village)

    if rate_type:
        query = query.where(Worker.rate_type == rate_type)

    if min_men_rate is not None:
        query = query.where(Worker.men_rate_value.is_not(None), Worker.men_rate_value >= min_men_rate)

    if max_men_rate is not None:
        query = query.where(Worker.men_rate_value.is_not(None), Worker.men_rate_value <= max_men_rate)

    if min_women_rate is not None:
        query = query.where(Worker.women_rate_value.is_not(None), Worker.women_rate_value >= min_women_rate)

    if max_women_rate is not None:
        query = query.where(Worker.women_rate_value.is_not(None), Worker.women_rate_value <= max_women_rate)

    if work_date:
        requested_slot = work_slot or "full_day"
        slot_match = (
            select(WorkerAvailabilitySlot.id)
            .where(
                WorkerAvailabilitySlot.worker_id == Worker.id,
                WorkerAvailabilitySlot.work_date == work_date,
                WorkerAvailabilitySlot.slot_type == requested_slot,
            )
            .exists()
        )
        if requested_slot == "full_day":
            work_date_token = f"%,{work_date.isoformat()},%"
            day_token = f"%,{weekday_name(work_date)},%"
            query = query.where(
                or_(
                    slot_match,
                    Worker.available_dates.like(work_date_token),
                    Worker.available_days.like(day_token),
                )
            )
        else:
            query = query.where(slot_match)

    query = query.order_by(Worker.created_at.desc())
    workers = db.scalars(query).all()

    if work_date:
        requested_slot = work_slot or "full_day"
        for worker in workers:
            remaining_men, remaining_women = remaining_capacity_for_slot(
                db,
                worker,
                work_date,
                requested_slot,
            )
            worker.remaining_men_count = remaining_men
            worker.remaining_women_count = remaining_women

    if near_latitude is not None and near_longitude is not None:
        filtered: list[Worker] = []
        for worker in workers:
            if worker.latitude is None or worker.longitude is None:
                worker.distance_km = None
                continue

            distance = _distance_km(near_latitude, near_longitude, worker.latitude, worker.longitude)
            worker.distance_km = round(distance, 2)

            if max_distance_km is not None and distance > max_distance_km:
                continue

            filtered.append(worker)

        workers = filtered

        if sort_by == "distance":
            workers.sort(key=lambda item: item.distance_km if item.distance_km is not None else float("inf"))

    return workers


def update_worker_availability(
    db: Session,
    worker_id: UUID,
    payload: WorkerAvailabilityUpdate,
    owner_phone: str | None = None,
) -> Worker | None:
    worker = db.get(Worker, worker_id)
    if not worker:
        return None

    if owner_phone and worker.phone != owner_phone:
        return None

    worker.available = payload.available
    db.commit()
    db.refresh(worker)
    return worker


def delete_worker(
    db: Session,
    worker_id: UUID,
    owner_phone: str | None = None,
) -> bool:
    worker = db.get(Worker, worker_id)
    if not worker:
        return False

    if owner_phone and worker.phone != owner_phone:
        return False

    booking_ids = db.scalars(select(Booking.id).where(Booking.worker_id == worker_id)).all()
    if booking_ids:
        db.execute(delete(BookingMessage).where(BookingMessage.booking_id.in_(booking_ids)))
        db.execute(delete(BookingEvent).where(BookingEvent.booking_id.in_(booking_ids)))
        db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))

    db.delete(worker)
    db.commit()
    return True


def update_worker_profile(
    db: Session,
    worker_id: UUID,
    payload: WorkerUpdate,
    owner_phone: str | None = None,
) -> Worker | None:
    worker = db.get(Worker, worker_id)
    if not worker:
        return None

    if owner_phone and worker.phone != owner_phone:
        return None

    windows = _normalized_windows(payload.available_dates, payload.availability_windows)

    worker.name = payload.name
    worker.village = payload.village
    worker.address = payload.address
    worker.latitude = payload.latitude
    worker.longitude = payload.longitude
    worker.men_count = payload.men_count
    worker.women_count = payload.women_count
    worker.rate_type = payload.rate_type
    worker.men_rate_value = payload.men_rate_value
    worker.women_rate_value = payload.women_rate_value
    worker.overtime_open = payload.overtime_open
    worker.overtime_price = payload.overtime_price
    worker.overtime_note = payload.overtime_note
    worker.available_dates = _dates_to_storage(_full_day_dates_from_windows(windows))

    _sync_worker_slots(db, worker, windows)

    db.commit()
    db.refresh(worker)
    return worker
