from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone

from .models import Hall, Performance, Play, Seat
from .services import ReservationError, create_reservation


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
