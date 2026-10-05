import math
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connection

from reservation.services import ReservationError, expire_reservations


class Command(BaseCommand):
    help = "Expire overdue holds and approval requests; use --watch for the timer."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=float, default=1)

    def handle(self, *args, **options):
        if not math.isfinite(options["interval"]) or options["interval"] <= 0:
            raise CommandError("--interval must be positive")
        try:
            while True:
                if not connection.in_atomic_block:
                    close_old_connections()
                try:
                    count = expire_reservations()
                except ReservationError as error:
                    if not options["watch"] or error.code != "busy":
                        raise CommandError(str(error)) from error
                    self.stderr.write(str(error))
                else:
                    if count or not options["watch"]:
                        self.stdout.write(f"Expired {count} reservation(s).")
                if not options["watch"]:
                    break
                time.sleep(options["interval"])
        except KeyboardInterrupt:
            self.stdout.write("Expiration timer stopped.")
