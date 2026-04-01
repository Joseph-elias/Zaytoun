from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.worker import Worker

BOOKING_CAPACITY_LOCK_STATUSES = ("confirmed", "accepted")


def weekday_name(work_date: date) -> str:
    return work_date.strftime("%A").lower()


def worker_available_on_date(worker: Worker, work_date: date) -> bool:
    # Primary path: exact calendar dates.
    token = f",{work_date.isoformat()},"
    if token in (worker.available_dates or ""):
        return True

    # Legacy fallback for old profiles that only had weekdays.
    day_name = weekday_name(work_date)
    return f",{day_name}," in (worker.available_days or "")


def remaining_capacity_for_date(
    db: Session,
    worker: Worker,
    work_date: date,
    *,
    exclude_booking_id: UUID | None = None,
) -> tuple[int, int]:
    requested_sum_query = select(
        func.coalesce(func.sum(Booking.requested_men), 0),
        func.coalesce(func.sum(Booking.requested_women), 0),
    ).where(
        Booking.worker_id == worker.id,
        Booking.work_date == work_date,
        Booking.status.in_(BOOKING_CAPACITY_LOCK_STATUSES),
    )

    if exclude_booking_id is not None:
        requested_sum_query = requested_sum_query.where(Booking.id != exclude_booking_id)

    requested_men, requested_women = db.execute(requested_sum_query).one()

    remaining_men = max(0, worker.men_count - int(requested_men or 0))
    remaining_women = max(0, worker.women_count - int(requested_women or 0))
    return remaining_men, remaining_women
