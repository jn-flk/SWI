"""Reservation use cases. All application writes must go through this module."""

from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q
from django.utils import timezone

from . import notifications
from .models import Performance, Reservation, ReservationSeat, Seat

Status = Reservation.Status
ACTIVE_STATUSES = (Status.DRAFT, Status.PENDING_APPROVAL, Status.CONFIRMED)


class ReservationError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _atomic_operation(function):
    """Commit an expiry even when the requested operation is then rejected."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            with transaction.atomic():
                result = function(*args, **kwargs)
        except IntegrityError as error:
            raise ReservationError("conflict", "Sedadla již nejsou dostupná.") from error
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            raise ReservationError(
                "busy", "Databáze právě zpracovává jinou rezervaci; zopakujte požadavek."
            ) from error
        if isinstance(result, ReservationError):
            raise result
        return result
    return wrapped


def _now(value):
    value = value if value is not None else timezone.now()
    if timezone.is_naive(value):
        raise ReservationError("invalid_time", "Čas musí obsahovat časové pásmo.")
    return value


def _authorize(actor):
    if actor is None or not actor.is_authenticated or not actor.is_active:
        raise ReservationError("forbidden", "Je vyžadován aktivní přihlášený uživatel.")


def _authorize_owner(actor, reservation):
    _authorize(actor)
    if reservation.owner_id != actor.pk and not actor.has_perm("reservation.change_reservation"):
        raise ReservationError("forbidden", "K této rezervaci nemáte oprávnění.")


def _performance(performance_id, *, lock=False):
    if type(performance_id) is not int or performance_id <= 0:
        raise ReservationError("invalid_id", "ID představení musí být kladné celé číslo.")
    query = Performance.objects.select_related("play", "hall")
    if lock:
        query = query.select_for_update()
    try:
        performance = query.get(pk=performance_id)
    except Performance.DoesNotExist as error:
        raise ReservationError("not_found", "Představení neexistuje.") from error
    if performance.play.duration <= timedelta(0):
        raise ReservationError("invalid_interval", "Představení musí mít kladnou délku.")
    return performance


def _reservation(reservation_id):
    if type(reservation_id) is not int or reservation_id <= 0:
        raise ReservationError("invalid_id", "ID rezervace musí být kladné celé číslo.")
    try:
        # Lock the performance first in every writer, then its reservation.
        performance_id = Reservation.objects.values_list("performance_id", flat=True).get(
            pk=reservation_id
        )
    except Reservation.DoesNotExist as error:
        raise ReservationError("not_found", "Rezervace neexistuje.") from error
    performance = _performance(performance_id, lock=True)
    reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
    reservation.performance = performance
    return reservation


def _seats(performance, seat_ids):
    if not isinstance(seat_ids, (list, tuple)) or not seat_ids:
        raise ReservationError("invalid_seats", "Vyberte alespoň jedno sedadlo.")
    if any(type(seat_id) is not int or seat_id <= 0 for seat_id in seat_ids):
        raise ReservationError("invalid_seats", "ID sedadel musí být kladná celá čísla.")
    if len(set(seat_ids)) != len(seat_ids):
        raise ReservationError("invalid_seats", "Výběr obsahuje duplicitní sedadla.")
    seats = list(Seat.objects.filter(pk__in=seat_ids).order_by("pk"))
    if len(seats) != len(seat_ids):
        raise ReservationError("not_found", "Některé sedadlo neexistuje.")
    if any(seat.hall_id != performance.hall_id for seat in seats):
        raise ReservationError("wrong_hall", "Sedadla musí patřit do sálu představení.")
    return seats


def _requires_approval(performance, seats):
    return (
        len(seats) > settings.RESERVATION_DIRECT_SEAT_LIMIT
        or len(seats) == performance.hall.seats.count()
    )


def _check_lead_time(performance, now, approval_required):
    if performance.start_at - now <= timedelta(minutes=settings.RESERVATION_CUTOFF_MINUTES):
        raise ReservationError("too_late", "Rezervace nelze přijmout 15 minut před začátkem.")
    if approval_required and performance.start_at - now < timedelta(
        hours=settings.RESERVATION_APPROVAL_HOURS
    ):
        raise ReservationError("approval_too_late", "Na schválení musí zbývat alespoň 24 hodin.")


def _notify(reservation, event):
    transaction.on_commit(
        lambda: notifications.notify(reservation.pk, event), robust=True
    )


def _set_status(reservation, status):
    reservation.status = status
    if status != Status.DRAFT:
        reservation.hold_until = None
    if status != Status.PENDING_APPROVAL:
        reservation.approval_deadline = None
    reservation.save(update_fields=["status", "hold_until", "approval_deadline"])
    if status not in ACTIVE_STATUSES:
        reservation.allocations.update(active=False)


def _expire_one(reservation, now):
    deadline = (
        reservation.hold_until if reservation.status == Status.DRAFT
        else reservation.approval_deadline if reservation.status == Status.PENDING_APPROVAL
        else None
    )
    if deadline is not None and now >= deadline:
        _set_status(reservation, Status.EXPIRED)
        _notify(reservation, "expired")
        return True
    return False


def _expire_for_performance(performance, now):
    query = Reservation.objects.select_for_update().filter(performance=performance).filter(
        Q(status=Status.DRAFT, hold_until__lte=now)
        | Q(status=Status.PENDING_APPROVAL, approval_deadline__lte=now)
    )
    return sum(_expire_one(reservation, now) for reservation in query)


def check_availability(performance_id, seat_ids=None, *, start=None, end=None, now=None):
    """Read-only snapshot for the performance; half-open interval queries are optional."""
    now = _now(now)
    performance = _performance(performance_id)
    if (start is None) != (end is None):
        raise ReservationError("invalid_interval", "Zadejte začátek i konec intervalu.")
    performance_end = performance.start_at + performance.play.duration
    start = performance.start_at if start is None else _now(start)
    end = performance_end if end is None else _now(end)
    if start >= end:
        raise ReservationError("invalid_interval", "Začátek musí být před koncem.")
    seats = (
        list(performance.hall.seats.order_by("pk"))
        if seat_ids is None else _seats(performance, seat_ids)
    )
    overlaps = start < performance_end and performance.start_at < end
    blockers = ReservationSeat.objects.filter(
        performance=performance, active=True
    ).filter(
        Q(reservation__status=Status.CONFIRMED)
        | Q(reservation__status=Status.DRAFT, reservation__hold_until__gt=now)
        | Q(reservation__status=Status.PENDING_APPROVAL, reservation__approval_deadline__gt=now)
    )
    blocked = set(blockers.values_list("seat_id", flat=True)) if overlaps else set()
    return {seat.pk: seat.is_active and seat.pk not in blocked for seat in seats}


@_atomic_operation
def create_reservation(actor, performance_id, seat_ids, *, now=None):
    _authorize(actor)
    performance = _performance(performance_id, lock=True)
    now = _now(now)
    seats = _seats(performance, seat_ids)
    if any(not seat.is_active for seat in seats):
        raise ReservationError("inactive_seat", "Neaktivní sedadlo nelze rezervovat.")
    _check_lead_time(performance, now, _requires_approval(performance, seats))
    _expire_for_performance(performance, now)
    if ReservationSeat.objects.filter(
        performance=performance, seat__in=seats, active=True
    ).exists():
        return ReservationError("unavailable", "Některé sedadlo je již blokováno.")
    reservation = Reservation.objects.create(
        owner=actor, performance=performance, status=Status.DRAFT,
        hold_until=now + timedelta(minutes=settings.RESERVATION_HOLD_MINUTES),
    )
    ReservationSeat.objects.bulk_create([
        ReservationSeat(reservation=reservation, performance=performance, seat=seat)
        for seat in seats
    ])
    return reservation


@_atomic_operation
def confirm_reservation(actor, reservation_id, *, now=None):
    reservation = _reservation(reservation_id)
    _authorize_owner(actor, reservation)
    now = _now(now)
    if _expire_one(reservation, now):
        return ReservationError("expired", "Držení rezervace vypršelo.")
    if reservation.status != Status.DRAFT:
        return ReservationError("invalid_state", "Potvrdit lze pouze DRAFT.")
    seats = list(reservation.seats.all())
    if any(not seat.is_active for seat in seats):
        return ReservationError("inactive_seat", "Rezervace obsahuje neaktivní sedadlo.")
    approval_required = _requires_approval(reservation.performance, seats)
    _check_lead_time(reservation.performance, now, approval_required)
    if approval_required:
        reservation.approval_deadline = now + timedelta(hours=settings.RESERVATION_APPROVAL_HOURS)
        _set_status(reservation, Status.PENDING_APPROVAL)
        _notify(reservation, "approval_requested")
    else:
        _set_status(reservation, Status.CONFIRMED)
    return reservation


@_atomic_operation
def cancel_reservation(actor, reservation_id, *, now=None):
    reservation = _reservation(reservation_id)
    _authorize_owner(actor, reservation)
    now = _now(now)
    if reservation.status == Status.CANCELLED:
        return reservation
    if _expire_one(reservation, now):
        return ReservationError("expired", "Rezervace již vypršela.")
    if reservation.status not in ACTIVE_STATUSES:
        return ReservationError("invalid_state", "Tento stav nelze zrušit.")
    if now >= reservation.performance.start_at:
        return ReservationError("too_late", "Představení již začalo.")
    _set_status(reservation, Status.CANCELLED)
    return reservation


@_atomic_operation
def approve_reservation(actor, reservation_id, *, approve=True, now=None):
    _authorize(actor)
    if not actor.has_perm("reservation.approve_reservation"):
        raise ReservationError("forbidden", "Nemáte oprávnění schvalovat rezervace.")
    if type(approve) is not bool:
        raise ReservationError("invalid_decision", "Rozhodnutí musí být true nebo false.")
    reservation = _reservation(reservation_id)
    now = _now(now)
    if _expire_one(reservation, now):
        return ReservationError("expired", "Lhůta pro schválení vypršela.")
    if reservation.status != Status.PENDING_APPROVAL:
        return ReservationError("invalid_state", "Rozhodnout lze pouze PENDING_APPROVAL.")
    if now >= reservation.performance.start_at:
        _set_status(reservation, Status.EXPIRED)
        _notify(reservation, "expired")
        return ReservationError("expired", "Představení již začalo.")
    _set_status(reservation, Status.CONFIRMED if approve else Status.REJECTED)
    _notify(reservation, "approved" if approve else "rejected")
    return reservation


@_atomic_operation
def touch_reservation(actor, reservation_id, *, now=None):
    """Explicit session activity renews DRAFT, never resurrects an expired hold."""
    reservation = _reservation(reservation_id)
    _authorize_owner(actor, reservation)
    now = _now(now)
    if _expire_one(reservation, now):
        return ReservationError("expired", "Držení rezervace vypršelo.")
    if reservation.status != Status.DRAFT:
        return ReservationError("invalid_state", "Aktivitu lze obnovit pouze pro DRAFT.")
    reservation.hold_until = min(
        now + timedelta(minutes=settings.RESERVATION_HOLD_MINUTES),
        reservation.performance.start_at,
    )
    reservation.save(update_fields=["hold_until"])
    return reservation


@_atomic_operation
def expire_reservations(*, now=None, performance_id=None):
    """Timer entry point; idempotent, including after an application restart."""
    performances = Performance.objects.select_for_update().order_by("pk")
    if performance_id is not None:
        performances = performances.filter(pk=performance_id)
    now = _now(now)
    return sum(_expire_for_performance(performance, now) for performance in performances)
