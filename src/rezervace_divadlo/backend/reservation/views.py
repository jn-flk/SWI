"""Frontend pages. Reservation writes go through services.py only."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import services
from .forms import ContactForm, SeatSelectionForm
from .models import Performance, Reservation
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


def _seat_rows(performance, availability, selected):
    rows = {}
    for seat in performance.hall.seats.order_by("row", "number"):
        rows.setdefault(seat.row, []).append({
            "seat": seat,
            "available": availability[seat.pk],
            "selected": str(seat.pk) in selected,
        })
    return rows.items()


def performance_list(request):
    performances = Performance.objects.select_related("play", "hall").filter(
        start_at__gt=timezone.now()
    ).order_by("start_at")
    return render(request, "performances/performance_list.html", {"performances": performances})


def performance_detail(request, pk):
    performance = _performance(pk)
    dates = performance.play.performances.select_related("hall").filter(
        start_at__gt=timezone.now()
    ).order_by("start_at")
    return render(request, "performances/performance_detail.html", {
        "performance": performance, "dates": dates,
    })


@login_required
def seat_selection(request, pk):
    performance = _performance(pk)
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
