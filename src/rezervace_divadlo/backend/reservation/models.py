from django.conf import settings
from django.db import models


class Play(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration = models.DurationField()

class Hall(models.Model):
    name = models.CharField(max_length=100)

class Seat(models.Model):
    hall = models.ForeignKey(
        Hall,
        on_delete=models.CASCADE,
        related_name="seats",
    )
    row = models.PositiveIntegerField()
    number = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hall", "row", "number"],
                name="unique_seat_in_hall",
            )
        ]

class Performance(models.Model):
    play = models.ForeignKey(
        Play,
        on_delete=models.CASCADE,
        related_name="performances",
    )
    start_at = models.DateTimeField()
    hall = models.ForeignKey(
        Hall,
        on_delete=models.CASCADE,
        related_name="performances",
    )


class Reservation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        PENDING_APPROVAL = "PENDING_APPROVAL"
        CONFIRMED = "CONFIRMED"
        CANCELLED = "CANCELLED"
        REJECTED = "REJECTED"
        EXPIRED = "EXPIRED"

    performance = models.ForeignKey(
        Performance,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,  # Existing C01 reservations have no recorded owner.
        related_name="reservations",
    )
    seats = models.ManyToManyField(Seat, through="ReservationSeat")
    status = models.CharField(max_length=20, choices=Status, default=Status.DRAFT)
    hold_until = models.DateTimeField(null=True, blank=True)
    approval_deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("approve_reservation", "Can approve or reject reservations")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[
                    "DRAFT", "PENDING_APPROVAL", "CONFIRMED",
                    "CANCELLED", "REJECTED", "EXPIRED",
                ]),
                name="valid_reservation_status",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="DRAFT") | models.Q(hold_until__isnull=False),
                name="draft_has_hold_deadline",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="PENDING_APPROVAL")
                | models.Q(approval_deadline__isnull=False),
                name="pending_has_approval_deadline",
            ),
        ]


class ReservationSeat(models.Model):
    """Keeps seat history; only active allocations must be exclusive."""

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="allocations"
    )
    performance = models.ForeignKey(Performance, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reservation", "seat"], name="unique_seat_per_reservation"
            ),
            models.UniqueConstraint(
                fields=["performance", "seat"],
                condition=models.Q(active=True),
                name="unique_active_performance_seat",
            )
        ]
