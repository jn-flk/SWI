from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone

from .models import Hall, Performance, Play, Reservation, Seat
from .services import ReservationError, confirm_reservation, create_reservation


class ReservationConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        now = timezone.now().replace(microsecond=0)
        self.user = get_user_model().objects.create_user(username="concurrent")
        hall = Hall.objects.create(name="Concurrency Hall")
        seat = Seat.objects.create(hall=hall, row=1, number=1)
        play = Play.objects.create(title="Concurrency Test", duration=timedelta(hours=2))
        self.performance = Performance.objects.create(
            hall=hall, play=play, start_at=now + timedelta(days=1)
        )
        self.seat = seat
        self.now = now

    def test_concurrent_creation_has_one_winner_for_one_seat(self):
        workers = 2
        barrier = Barrier(workers)

        def attempt():
            from django.db import close_old_connections

            close_old_connections()
            try:
                barrier.wait(timeout=10)
                create_reservation(
                    self.user,
                    self.performance.pk,
                    [self.seat.pk],
                    now=self.now,
                )
                return "created"
            except ReservationError as error:
                return error.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(lambda _: attempt(), range(workers)))

        self.assertEqual(outcomes.count("created"), 1)
        self.assertEqual(
            sum(outcome in {"conflict", "busy", "unavailable"} for outcome in outcomes),
            1,
        )

    def test_concurrent_confirm_has_one_winner_for_one_reservation(self):
        workers = 2
        barrier = Barrier(workers)
        # A second seat keeps this off the whole-hall approval path.
        Seat.objects.create(hall_id=self.seat.hall_id, row=1, number=2)
        reservation = create_reservation(
            self.user, self.performance.pk, [self.seat.pk], now=self.now
        )

        def attempt():
            from django.db import close_old_connections

            close_old_connections()
            try:
                barrier.wait(timeout=10)
                confirm_reservation(self.user, reservation.pk, now=self.now)
                return "confirmed"
            except ReservationError as error:
                return error.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(lambda _: attempt(), range(workers)))

        self.assertEqual(outcomes.count("confirmed"), 1)
        self.assertEqual(
            sum(outcome in {"invalid_state", "busy"} for outcome in outcomes),
            1,
        )
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.allocations.filter(active=True).count(), 1)
