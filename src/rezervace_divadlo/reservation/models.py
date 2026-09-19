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
    performance = models.ForeignKey(
        Performance,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    seats = models.ManyToManyField(
        Seat,
        related_name="reservations",
    )
    created_at = models.DateTimeField(auto_now_add=True)