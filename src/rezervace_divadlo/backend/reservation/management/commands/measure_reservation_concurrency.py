import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections
from django.utils import timezone

from reservation.models import Hall, Performance, Play, Reservation, Seat
from reservation.services import ReservationError, create_reservation


class Command(BaseCommand):
    help = "Measure concurrent SQLite reservation attempts for one seat."

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=20)
        parser.add_argument("--rounds", type=int, default=5)

    def handle(self, *args, **options):
        workers = options["workers"]
        rounds = options["rounds"]
        if workers <= 1 or rounds <= 0:
            raise CommandError("--workers must be greater than 1 and --rounds must be positive")

        suffix = uuid4().hex
        now = timezone.now().replace(microsecond=0)
        user = None
        hall = play = performance = seat = None
        try:
            try:
                user = get_user_model().objects.create_user(username=f"measure-{suffix}")
            except OperationalError as error:
                raise CommandError(
                    "Database is not initialized; run 'manage.py migrate' first."
                ) from error
            hall = Hall.objects.create(name=f"Measure Hall {suffix}")
            seat = Seat.objects.create(hall=hall, row=1, number=1)
            play = Play.objects.create(
                title=f"Measure Play {suffix}", duration=timedelta(hours=2)
            )
            performance = Performance.objects.create(
                hall=hall, play=play, start_at=now + timedelta(days=1)
            )
            results = []
            measurement_started = time.perf_counter()
            for round_number in range(rounds):
                results.extend(self._run_round(workers, user.pk, performance.pk, seat.pk, now))
                self.stdout.write(f"round={round_number + 1}/{rounds}")
            measurement_seconds = time.perf_counter() - measurement_started

            latencies = [result["latency_ms"] for result in results]
            summary = {
                "workers": workers,
                "rounds": rounds,
                "attempts": len(results),
                "created": sum(result["outcome"] == "created" for result in results),
                "conflict": sum(
                    result["outcome"] in {"conflict", "unavailable"} for result in results
                ),
                "busy": sum(result["outcome"] == "busy" for result in results),
                "latency_ms": {
                    "min": round(min(latencies), 2),
                    "median": round(statistics.median(latencies), 2),
                    "max": round(max(latencies), 2),
                },
                "wall_time_seconds": round(measurement_seconds, 3),
                "throughput_attempts_per_second": round(len(results) / measurement_seconds, 2),
            }
            self.stdout.write(json.dumps(summary, indent=2))
        finally:
            if performance is not None:
                performance.delete()
            if play is not None:
                play.delete()
            if seat is not None:
                seat.delete()
            if hall is not None:
                hall.delete()
            if user is not None:
                user.delete()

    @staticmethod
    def _run_round(workers, user_id, performance_id, seat_id, now):
        barrier = Barrier(workers)

        def attempt():
            started = time.perf_counter()
            close_old_connections()
            try:
                barrier.wait(timeout=30)
                user = get_user_model().objects.get(pk=user_id)
                create_reservation(user, performance_id, [seat_id], now=now)
                outcome = "created"
            except ReservationError as error:
                if error.code not in {"conflict", "busy", "unavailable"}:
                    raise
                outcome = error.code
            except OperationalError as error:
                if "locked" not in str(error).lower():
                    raise
                outcome = "busy"
            finally:
                close_old_connections()
            return {
                "outcome": outcome,
                "latency_ms": (time.perf_counter() - started) * 1000,
            }

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda _: attempt(), range(workers)))
        Reservation.objects.filter(performance_id=performance_id).delete()
        return results
