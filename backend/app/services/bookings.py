from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.booking_event import BookingEvent
from app.models.booking_message import BookingMessage
from app.models.olive_season import FarmerOliveSeason
from app.models.user import User
from app.models.worker import Worker
from app.schemas.booking import BookingCreate, BookingProposalUpdate, BookingStatus, WorkerBookingResponse
from app.services.capacity import remaining_capacity_for_slot, weekday_name, worker_available_on_slot


def _booking_select() -> Select:
    return select(Booking, Worker, User).join(Worker, Worker.id == Booking.worker_id).join(User, User.id == Booking.farmer_user_id)


def _resolved_work_slot(booking: Booking) -> str:
    return booking.work_slot or "full_day"


def _to_out_row(row) -> dict:
    booking, worker, farmer = row
    resolved_day = booking.day
    if booking.work_date is not None:
        resolved_day = weekday_name(booking.work_date)

    return {
        "id": booking.id,
        "season_id": booking.season_id,
        "worker_id": booking.worker_id,
        "worker_name": worker.name,
        "worker_phone": worker.phone,
        "worker_village": worker.village,
        "farmer_user_id": booking.farmer_user_id,
        "farmer_name": farmer.full_name,
        "farmer_phone": farmer.phone,
        "work_date": booking.work_date,
        "work_slot": _resolved_work_slot(booking),
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


def _is_confirmed(status: str) -> bool:
    return status in {"confirmed", "accepted"}


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
    work_slot: str,
    requested_men: int,
    requested_women: int,
    *,
    exclude_booking_id: UUID | None = None,
) -> None:
    remaining_men, remaining_women = remaining_capacity_for_slot(
        db,
        worker,
        work_date,
        work_slot,
        exclude_booking_id=exclude_booking_id,
    )
    if requested_men > remaining_men:
        raise ValueError(f"Requested men exceeds remaining team capacity ({remaining_men}) for selected date and slot")
    if requested_women > remaining_women:
        raise ValueError(f"Requested women exceeds remaining team capacity ({remaining_women}) for selected date and slot")


def _duplicate_booking_exists(
    db: Session,
    *,
    worker_id: UUID,
    farmer_user_id: UUID,
    work_date,
    work_slot: str,
    exclude_booking_id: UUID | None = None,
) -> bool:
    query = select(Booking).where(
        Booking.worker_id == worker_id,
        Booking.farmer_user_id == farmer_user_id,
        Booking.work_date == work_date,
        Booking.status.in_(["pending_worker", "pending", "pending_farmer", "confirmed", "accepted"]),
    )

    if work_slot == "full_day":
        query = query.where(or_(Booking.work_slot == "full_day", Booking.work_slot.is_(None)))
    else:
        query = query.where(Booking.work_slot == work_slot)

    if exclude_booking_id is not None:
        query = query.where(Booking.id != exclude_booking_id)

    return db.scalar(query) is not None


def create_bookings_for_worker(db: Session, worker: Worker, farmer: User, payload: BookingCreate) -> list[dict]:
    created: list[Booking] = []
    requested_season_ids = {
        season_id
        for season_id in [payload.season_id, *(item.season_id for item in payload.requests)]
        if season_id is not None
    }
    owned_season_ids: set[UUID] = set()
    if requested_season_ids:
        owned_season_ids = set(
            db.scalars(
                select(FarmerOliveSeason.id).where(
                    FarmerOliveSeason.farmer_user_id == farmer.id,
                    FarmerOliveSeason.id.in_(requested_season_ids),
                )
            ).all()
        )
        if owned_season_ids != requested_season_ids:
            raise ValueError("Season record not found for booking")

    for item in payload.requests:
        resolved_season_id = item.season_id if item.season_id is not None else payload.season_id

        if not worker_available_on_slot(db, worker, item.work_date, item.work_slot):
            raise ValueError(
                f"Worker is not available on selected date {item.work_date.isoformat()} for slot {item.work_slot}"
            )

        _ensure_capacity(
            db,
            worker,
            item.work_date,
            item.work_slot,
            item.requested_men,
            item.requested_women,
        )

        if _duplicate_booking_exists(
            db,
            worker_id=worker.id,
            farmer_user_id=farmer.id,
            work_date=item.work_date,
            work_slot=item.work_slot,
        ):
            raise ValueError(
                f"Booking already exists for selected date {item.work_date.isoformat()} and slot {item.work_slot}"
            )

        booking = Booking(
            worker_id=worker.id,
            farmer_user_id=farmer.id,
            season_id=resolved_season_id,
            work_date=item.work_date,
            work_slot=item.work_slot,
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
            f"{item.work_date.isoformat()} ({item.work_slot}): {item.requested_men} men, {item.requested_women} women",
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

        proposed_slot = payload.work_slot or _resolved_work_slot(booking)
        if not worker_available_on_slot(db, worker, booking.work_date, proposed_slot):
            raise ValueError(
                f"Worker is not available on selected date {booking.work_date.isoformat()} for slot {proposed_slot}"
            )

        _ensure_capacity(
            db,
            worker,
            booking.work_date,
            proposed_slot,
            payload.requested_men,
            payload.requested_women,
            exclude_booking_id=booking.id,
        )

        booking.requested_men = payload.requested_men
        booking.requested_women = payload.requested_women
        booking.work_slot = proposed_slot
        booking.note = payload.note
        booking.status = "pending_farmer"
        _record_event(
            db,
            booking.id,
            worker_user.id,
            "worker_proposed_changes",
            f"{payload.requested_men} men, {payload.requested_women} women, slot={proposed_slot}",
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
            _resolved_work_slot(booking),
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


def update_booking_proposal(
    db: Session,
    booking_id: UUID,
    current_user: User,
    payload: BookingProposalUpdate,
) -> dict | None:
    row = db.execute(_booking_select().where(Booking.id == booking_id)).first()
    if not _assert_booking_access(row, current_user):
        return None

    booking, worker, _ = row
    if _is_confirmed(booking.status):
        raise ValueError("Confirmed bookings cannot be modified")

    work_date = payload.work_date if payload.work_date is not None else booking.work_date
    work_slot = payload.work_slot if payload.work_slot is not None else _resolved_work_slot(booking)
    requested_men = payload.requested_men if payload.requested_men is not None else booking.requested_men
    requested_women = payload.requested_women if payload.requested_women is not None else booking.requested_women

    if work_date is None:
        raise ValueError("Cannot update legacy booking without exact date")
    if requested_men + requested_women < 1:
        raise ValueError("At least one person is required")
    if not worker_available_on_slot(db, worker, work_date, work_slot):
        raise ValueError(f"Worker is not available on selected date {work_date.isoformat()} for slot {work_slot}")

    if _duplicate_booking_exists(
        db,
        worker_id=booking.worker_id,
        farmer_user_id=booking.farmer_user_id,
        work_date=work_date,
        work_slot=work_slot,
        exclude_booking_id=booking.id,
    ):
        raise ValueError(f"Booking already exists for selected date {work_date.isoformat()} and slot {work_slot}")

    _ensure_capacity(
        db,
        worker,
        work_date,
        work_slot,
        requested_men,
        requested_women,
        exclude_booking_id=booking.id,
    )

    booking.work_date = work_date
    booking.work_slot = work_slot
    booking.day = weekday_name(work_date)
    booking.requested_men = requested_men
    booking.requested_women = requested_women
    if payload.note is not None:
        booking.note = payload.note

    if current_user.role == "farmer":
        booking.status = "pending_worker"
        _record_event(
            db,
            booking.id,
            current_user.id,
            "farmer_updated_proposal",
            f"{work_date.isoformat()} ({work_slot}): {requested_men} men, {requested_women} women",
        )
    else:
        booking.status = "pending_farmer"
        _record_event(
            db,
            booking.id,
            current_user.id,
            "worker_updated_proposal",
            f"{work_date.isoformat()} ({work_slot}): {requested_men} men, {requested_women} women",
        )

    db.commit()
    db.refresh(booking)

    fresh = db.execute(_booking_select().where(Booking.id == booking.id)).first()
    return _to_out_row(fresh) if fresh else None


def delete_booking_proposal(
    db: Session,
    booking_id: UUID,
    current_user: User,
    *,
    force: bool = False,
) -> bool | None:
    row = db.execute(_booking_select().where(Booking.id == booking_id)).first()
    if not _assert_booking_access(row, current_user):
        return None

    booking, _, _ = row
    if _is_confirmed(booking.status) and not force:
        raise ValueError("Confirmed bookings cannot be deleted")

    db.execute(delete(BookingMessage).where(BookingMessage.booking_id == booking_id))
    db.execute(delete(BookingEvent).where(BookingEvent.booking_id == booking_id))
    db.delete(booking)
    db.commit()
    return True


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
