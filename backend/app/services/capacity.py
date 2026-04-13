from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.worker import Worker
from app.models.worker_availability_slot import WorkerAvailabilitySlot

BOOKING_CAPACITY_LOCK_STATUSES = ("confirmed", "accepted")
WORK_SLOT_TYPES = ("full_day", "extra_time")


def weekday_name(work_date: date) -> str:
    return work_date.strftime("%A").lower()


def worker_available_on_slot(db: Session, worker: Worker, work_date: date, work_slot: str) -> bool:
    if work_slot not in WORK_SLOT_TYPES:
        return False

    has_windows_for_date = db.scalar(
        select(func.count(WorkerAvailabilitySlot.id)).where(
            WorkerAvailabilitySlot.worker_id == worker.id,
            WorkerAvailabilitySlot.work_date == work_date,
        )
    )
    if has_windows_for_date:
        return bool(
            db.scalar(
                select(func.count(WorkerAvailabilitySlot.id)).where(
                    WorkerAvailabilitySlot.worker_id == worker.id,
                    WorkerAvailabilitySlot.work_date == work_date,
                    WorkerAvailabilitySlot.slot_type == work_slot,
                )
            )
        )

    if work_slot != "full_day":
        return False

    # Legacy fallback for old profiles where only date/day data existed.
    token = f",{work_date.isoformat()},"
    if token in (worker.available_dates or ""):
        return True

    day_name = weekday_name(work_date)
    return f",{day_name}," in (worker.available_days or "")


def remaining_capacity_for_slot(
    db: Session,
    worker: Worker,
    work_date: date,
    work_slot: str = "full_day",
    *,
    exclude_booking_id: UUID | None = None,
) -> tuple[int, int]:
    if work_slot not in WORK_SLOT_TYPES:
        raise ValueError("Invalid work slot")

    slot_filter = Booking.work_slot == work_slot
    if work_slot == "full_day":
        # Legacy rows may not have slot filled yet.
        slot_filter = or_(Booking.work_slot == "full_day", Booking.work_slot.is_(None))

    requested_sum_query = select(
        func.coalesce(func.sum(Booking.requested_men), 0),
        func.coalesce(func.sum(Booking.requested_women), 0),
    ).where(
        Booking.worker_id == worker.id,
        Booking.work_date == work_date,
        slot_filter,
        Booking.status.in_(BOOKING_CAPACITY_LOCK_STATUSES),
    )

    if exclude_booking_id is not None:
        requested_sum_query = requested_sum_query.where(Booking.id != exclude_booking_id)

    requested_men, requested_women = db.execute(requested_sum_query).one()

    remaining_men = max(0, worker.men_count - int(requested_men or 0))
    remaining_women = max(0, worker.women_count - int(requested_women or 0))
    return remaining_men, remaining_women


def worker_available_on_date(worker: Worker, work_date: date) -> bool:
    # Backward-compatible helper retained for legacy callers.
    token = f",{work_date.isoformat()},"
    if token in (worker.available_dates or ""):
        return True
    day_name = weekday_name(work_date)
    return f",{day_name}," in (worker.available_days or "")


def remaining_capacity_for_date(
    db: Session,
    worker: Worker,
    work_date: date,
    *,
    exclude_booking_id: UUID | None = None,
) -> tuple[int, int]:
    return remaining_capacity_for_slot(
        db,
        worker,
        work_date,
        "full_day",
        exclude_booking_id=exclude_booking_id,
    )
