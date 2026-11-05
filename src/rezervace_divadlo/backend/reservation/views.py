"""Frontend pages. Reservation writes go through services.py only."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Min
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from . import services
from .forms import ContactForm, SeatSelectionForm
from .models import Performance, Play, Reservation
from .services import ReservationError

Status = Reservation.Status


def _performance(pk):
    return get_object_or_404(Performance.objects.select_related("play", "hall"), pk=pk)


def _owned_reservation(request, pk):
    return get_object_or_404(
        Reservation.objects.select_related("performance__play", "performance__hall"),
        pk=pk, owner=request.user,
    )


def _not_draft(request, reservation):
    if reservation.status in (Status.CONFIRMED, Status.PENDING_APPROVAL):
        return redirect("reservation_success", pk=reservation.pk)
    messages.error(request, "Rezervace už není aktivní, vyberte sedadla znovu.")
    return redirect("seat_selection", pk=reservation.performance_id)


def _with_free_seats(performances):
    performances = list(performances)
    for performance in performances:
        performance.free_seats = sum(services.check_availability(performance.pk).values())
    return performances


def _seat_rows(performance, availability, selected):
    rows = {}
    for seat in performance.hall.seats.order_by("row", "number"):
        rows.setdefault(seat.row, []).append({
            "seat": seat,
            "available": availability[seat.pk],
            "selected": str(seat.pk) in selected,
        })
    return rows.items()


def register(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ""
    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        login(request, form.save())
        return redirect(next_url or "play_list")
    return render(request, "registration/register.html", {"form": form, "next": next_url})


def play_list(request):
    plays = Play.objects.filter(performances__start_at__gt=timezone.now()).annotate(
        date_count=Count("performances"), next_start=Min("performances__start_at"),
    ).order_by("next_start")
    return render(request, "plays/play_list.html", {"plays": plays})


def play_detail(request, pk):
    play = get_object_or_404(Play, pk=pk)
    dates = play.performances.select_related("hall").filter(
        start_at__gt=timezone.now()
    ).order_by("start_at")
    return render(request, "plays/play_detail.html", {
        "play": play, "dates": _with_free_seats(dates),
    })


@login_required
def seat_selection(request, pk):
    performance = _performance(pk)
    services.expire_reservations(performance_id=performance.pk)
    if request.method == "GET":
        services.release_draft_reservations(request.user, performance.pk)
    availability = services.check_availability(performance.pk)
    form = SeatSelectionForm(
        request.POST if request.method == "POST" else None,
        available_seat_ids=[seat_id for seat_id, free in availability.items() if free],
    )
    if form.is_bound and form.is_valid():
        try:
            reservation = services.create_reservation(
                request.user, performance.pk, form.cleaned_data["seats"]
            )
        except ReservationError as error:
            form.add_error(None, str(error))
            availability = services.check_availability(performance.pk)
        else:
            return redirect("reservation_form", pk=reservation.pk)
    return render(request, "halls/seat_selection.html", {
        "performance": performance,
        "form": form,
        "rows": _seat_rows(performance, availability, set(request.POST.getlist("seats"))),
    })


@login_required
def reservation_form(request, pk):
    reservation = _owned_reservation(request, pk)
    if reservation.status != Status.DRAFT:
        return _not_draft(request, reservation)
    form = ContactForm(request.POST if request.method == "POST" else None, instance=request.user)
    if form.is_bound and form.is_valid():
        form.save()
        try:
            services.touch_reservation(request.user, reservation.pk)
        except ReservationError as error:
            messages.error(request, str(error))
            return redirect("seat_selection", pk=reservation.performance_id)
        return redirect("reservation_summary", pk=reservation.pk)
    return render(request, "reservations/reservation_form.html", {
        "reservation": reservation, "form": form,
    })


@login_required
def reservation_summary(request, pk):
    reservation = _owned_reservation(request, pk)
    if reservation.status != Status.DRAFT:
        return _not_draft(request, reservation)
    if request.method == "POST":
        try:
            services.confirm_reservation(request.user, reservation.pk)
        except ReservationError as error:
            messages.error(request, str(error))
            return redirect("seat_selection", pk=reservation.performance_id)
        return redirect("reservation_success", pk=reservation.pk)
    return render(request, "reservations/reservation_summary.html", {
        "reservation": reservation, "seats": reservation.seats.order_by("row", "number"),
    })


@login_required
def reservation_success(request, pk):
    reservation = _owned_reservation(request, pk)
    if reservation.status not in (Status.CONFIRMED, Status.PENDING_APPROVAL):
        raise Http404
    return render(request, "reservations/reservation_success.html", {
        "reservation": reservation, "seats": reservation.seats.order_by("row", "number"),
    })
