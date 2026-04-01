from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.worker import Worker
from app.schemas.worker import WorkerAvailabilityUpdate, WorkerCreate
from app.services.capacity import remaining_capacity_for_date, weekday_name


def _dates_to_storage(dates: list[date]) -> str:
    iso_dates = sorted({value.isoformat() for value in dates})
    return "," + ",".join(iso_dates) + ","


def create_worker(db: Session, payload: WorkerCreate) -> Worker:
    data = payload.model_dump()
    data["available_dates"] = _dates_to_storage(payload.available_dates)
    worker = Worker(**data)
    db.add(worker)
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
) -> Sequence[Worker]:
    query = select(Worker)

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
        work_date_token = f"%,{work_date.isoformat()},%"
        day_token = f"%,{weekday_name(work_date)},%"
        query = query.where(
            or_(
                Worker.available_dates.like(work_date_token),
                Worker.available_days.like(day_token),
            )
        )

    query = query.order_by(Worker.created_at.desc())
    workers = db.scalars(query).all()

    if work_date:
        for worker in workers:
            remaining_men, remaining_women = remaining_capacity_for_date(db, worker, work_date)
            worker.remaining_men_count = remaining_men
            worker.remaining_women_count = remaining_women

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
