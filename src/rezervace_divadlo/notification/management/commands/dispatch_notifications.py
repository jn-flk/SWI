import math
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, close_old_connections

from notification.dispatcher import dispatch_notifications


class Command(BaseCommand):
    help = "Deliver due outbox notifications; use --watch for continuous dispatch."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=float, default=1)
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        if not math.isfinite(options["interval"]) or options["interval"] <= 0:
            raise CommandError("--interval must be positive and finite")
        if options["batch_size"] <= 0:
            raise CommandError("--batch-size must be positive")
        try:
            while True:
                close_old_connections()
                try:
                    counts = dispatch_notifications(batch_size=options["batch_size"])
                except OperationalError as error:
                    if not options["watch"] or "locked" not in str(error).lower():
                        raise CommandError(str(error)) from error
                    self.stderr.write(str(error))
                except (ValueError, ImportError) as error:
                    raise CommandError(str(error)) from error
                else:
                    if counts["attempted"] or not options["watch"]:
                        self.stdout.write(" ".join(f"{key}={value}" for key, value in counts.items()))
                if not options["watch"]:
                    break
                time.sleep(options["interval"])
        except KeyboardInterrupt:
            self.stdout.write("Notification dispatcher stopped.")
