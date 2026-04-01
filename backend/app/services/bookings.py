from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.booking_event import BookingEvent
from app.models.booking_message import BookingMessage
from app.models.user import User
from app.models.worker import Worker
from app.schemas.booking import BookingCreate, BookingStatus, WorkerBookingResponse
from app.services.capacity import remaining_capacity_for_date, weekday_name, worker_available_on_date


def _booking_select() -> Select:
    return select(Booking, Worker, User).join(Worker, Worker.id == Booking.worker_id).join(User, User.id == Booking.farmer_user_id)


def _to_out_row(row) -> dict:
    booking, worker, farmer = row
    resolved_day = booking.day
    if booking.work_date is not None:
        resolved_day = weekday_name(booking.work_date)

    return {
        "id": booking.id,
        "worker_id": booking.worker_id,
        "worker_name": worker.name,
        "worker_phone": worker.phone,
        "worker_village": worker.village,
        "farmer_user_id": booking.farmer_user_id,
        "farmer_name": farmer.full_name,
        "farmer_phone": farmer.phone,
        "work_date": booking.work_date,
        "day": resolved_day,
        "requested_men": booking.requested_men,
        "requested_women": booking.requested_women,
        "status": booking.status,
        "note": booking.note,
        "created_at": booking.created_at,
    }


def _assert_booking_access(row, current_user: User) -> bool:
    if not row:
        return False
    booking, worker, _ = row
    if current_user.role == "farmer":
        return booking.farmer_user_id == current_user.id
    if current_user.role == "worker":
        return worker.phone == current_user.phone
    return False


def _is_pending_worker(status: str) -> bool:
    return status in {"pending_worker", "pending"}


def _is_pending_farmer(status: str) -> bool:
    return status == "pending_farmer"


def _record_event(db: Session, booking_id: UUID, actor_user_id: UUID, action: str, details: str | None = None) -> None:
    db.add(
        BookingEvent(
            booking_id=booking_id,
            actor_user_id=actor_user_id,
            action=action,
            details=details,
        )
    )


def _ensure_capacity(
    db: Session,
    worker: Worker,
    work_date,
    requested_men: int,
    requested_women: int,
    *,
    exclude_booking_id: UUID | None = None,
) -> None:
    remaining_men, remaining_women = remaining_capacity_for_date(
        db,
        worker,
        work_date,
        exclude_booking_id=exclude_booking_id,
    )
    if requested_men > remaining_men:
        raise ValueError(f"Requested men exceeds remaining team capacity ({remaining_men}) for selected date")
    if requested_women > remaining_women:
        raise ValueError(f"Requested women exceeds remaining team capacity ({remaining_women}) for selected date")


def create_bookings_for_worker(db: Session, worker: Worker, farmer: User, payload: BookingCreate) -> list[dict]:
    created: list[Booking] = []

    for item in payload.requests:
        if not worker_available_on_date(worker, item.work_date):
            raise ValueError(f"Worker is not available on selected date {item.work_date.isoformat()}")

        _ensure_capacity(db, worker, item.work_date, item.requested_men, item.requested_women)

        existing = db.scalar(
            select(Booking).where(
                Booking.worker_id == worker.id,
                Booking.farmer_user_id == farmer.id,
                Booking.work_date == item.work_date,
                Booking.status.in_(["pending_worker", "pending", "pending_farmer", "confirmed", "accepted"]),
            )
        )
        if existing:
            raise ValueError(f"Booking already exists for selected date {item.work_date.isoformat()}")

        booking = Booking(
            worker_id=worker.id,
            farmer_user_id=farmer.id,
            work_date=item.work_date,
            day=weekday_name(item.work_date),
            requested_men=item.requested_men,
            requested_women=item.requested_women,
            note=payload.note,
            status="pending_worker",
        )
        db.add(booking)
        db.flush()
        _record_event(
            db,
            booking.id,
            farmer.id,
            "farmer_created_request",
            f"{item.work_date.isoformat()}: {item.requested_men} men, {item.requested_women} women",
        )
        created.append(booking)

    if not created:
        raise ValueError("No booking requests were created")

    db.commit()

    rows = db.execute(
        _booking_select().where(Booking.id.in_([booking.id for booking in created])).order_by(Booking.work_date.asc())
    ).all()
    return [_to_out_row(row) for row in rows]


def list_farmer_bookings(db: Session, farmer_user_id: UUID, status: BookingStatus | None = None) -> Sequence[dict]:
    query = _booking_select().where(Booking.farmer_user_id == farmer_user_id)
    if status:
        query = query.where(Booking.status == status)
    rows = db.execute(query.order_by(Booking.created_at.desc())).all()
    return [_to_out_row(row) for row in rows]


def list_worker_received_bookings(db: Session, worker_phone: str) -> Sequence[dict]:
    rows = db.execute(
        _booking_select().where(Worker.phone == worker_phone).order_by(Booking.created_at.desc())
    ).all()
    return [_to_out_row(row) for row in rows]


def worker_respond_to_booking(
    db: Session,
    booking_id: UUID,
    worker_user: User,
    payload: WorkerBookingResponse,
) -> dict | None:
    row = db.execute(_booking_select().where(Booking.id == booking_id, Worker.phone == worker_user.phone)).first()
    if not row:
        return None

    booking, worker, _ = row
    if not _is_pending_worker(booking.status):
        raise ValueError("Booking is not waiting for worker response")

    if payload.action == "reject":
        booking.status = "rejected"
        _record_event(db, booking.id, worker_user.id, "worker_rejected", None)
    elif payload.action == "accept":
        booking.status = "pending_farmer"
        _record_event(db, booking.id, worker_user.id, "worker_accepted", None)
    else:  # propose
        if payload.requested_men is None or payload.requested_women is None:
            raise ValueError("requested_men and requested_women are required for proposals")
        if payload.requested_men + payload.requested_women < 1:
            raise ValueError("At least one person is required")
        if booking.work_date is None:
            raise ValueError("Cannot propose changes for legacy booking without exact date")

        _ensure_capacity(
            db,
            worker,
            booking.work_date,
            payload.requested_men,
            payload.requested_women,
            exclude_booking_id=booking.id,
        )

        booking.requested_men = payload.requested_men
        booking.requested_women = payload.requested_women
        booking.note = payload.note
        booking.status = "pending_farmer"
        _record_event(
            db,
            booking.id,
            worker_user.id,
            "worker_proposed_changes",
            f"{payload.requested_men} men, {payload.requested_women} women",
        )

    db.commit()
    db.refresh(booking)

    fresh = db.execute(_booking_select().where(Booking.id == booking.id)).first()
    return _to_out_row(fresh) if fresh else None


def farmer_validate_booking(db: Session, booking_id: UUID, farmer_user: User, action: str) -> dict | None:
    row = db.execute(_booking_select().where(Booking.id == booking_id, Booking.farmer_user_id == farmer_user.id)).first()
    if not row:
        return None

    booking, worker, _ = row
    if not _is_pending_farmer(booking.status):
        raise ValueError("Booking is not waiting for farmer validation")

    if action == "confirm":
        if booking.work_date is None:
            raise ValueError("Cannot confirm legacy booking without exact date")
        _ensure_capacity(
            db,
            worker,
            booking.work_date,
            booking.requested_men,
            booking.requested_women,
            exclude_booking_id=booking.id,
        )
        booking.status = "confirmed"
        _record_event(db, booking.id, farmer_user.id, "farmer_confirmed", None)
    else:
        booking.status = "rejected"
        _record_event(db, booking.id, farmer_user.id, "farmer_rejected", None)

    db.commit()
    db.refresh(booking)

    fresh = db.execute(_booking_select().where(Booking.id == booking.id)).first()
    return _to_out_row(fresh) if fresh else None


def list_booking_messages(db: Session, booking_id: UUID, current_user: User) -> Sequence[dict] | None:
    booking_row = db.execute(_booking_select().where(Booking.id == booking_id)).first()
    if not _assert_booking_access(booking_row, current_user):
        return None

    rows = db.execute(
        select(BookingMessage, User)
        .join(User, User.id == BookingMessage.sender_user_id)
        .where(BookingMessage.booking_id == booking_id)
        .order_by(BookingMessage.created_at.asc())
    ).all()

    return [
        {
            "id": msg.id,
            "booking_id": msg.booking_id,
            "sender_user_id": msg.sender_user_id,
            "sender_name": sender.full_name,
            "sender_role": sender.role,
            "content": msg.content,
            "created_at": msg.created_at,
        }
        for msg, sender in rows
    ]


def create_booking_message(db: Session, booking_id: UUID, current_user: User, content: str) -> dict | None:
    booking_row = db.execute(_booking_select().where(Booking.id == booking_id)).first()
    if not _assert_booking_access(booking_row, current_user):
        return None

    message = BookingMessage(
        booking_id=booking_id,
        sender_user_id=current_user.id,
        content=content.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    row = db.execute(
        select(BookingMessage, User)
        .join(User, User.id == BookingMessage.sender_user_id)
        .where(BookingMessage.id == message.id)
    ).first()
    if not row:
        return None

    msg, sender = row
    return {
        "id": msg.id,
        "booking_id": msg.booking_id,
        "sender_user_id": msg.sender_user_id,
        "sender_name": sender.full_name,
        "sender_role": sender.role,
        "content": msg.content,
        "created_at": msg.created_at,
    }


def list_booking_events(db: Session, booking_id: UUID, current_user: User) -> Sequence[dict] | None:
    booking_row = db.execute(_booking_select().where(Booking.id == booking_id)).first()
    if not _assert_booking_access(booking_row, current_user):
        return None

    rows = db.execute(
        select(BookingEvent, User)
        .join(User, User.id == BookingEvent.actor_user_id)
        .where(BookingEvent.booking_id == booking_id)
        .order_by(BookingEvent.created_at.asc())
    ).all()

    return [
        {
            "id": event.id,
            "booking_id": event.booking_id,
            "actor_user_id": event.actor_user_id,
            "actor_name": actor.full_name,
            "actor_role": actor.role,
            "action": event.action,
            "details": event.details,
            "created_at": event.created_at,
        }
        for event, actor in rows
    ]
