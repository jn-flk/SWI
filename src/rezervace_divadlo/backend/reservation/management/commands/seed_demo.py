from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from reservation.models import Hall, Performance, Play, Seat


class Command(BaseCommand):
    help = "Create local demo data for the frontend (idempotent)."

    def handle(self, *args, **options):
        hall, _ = Hall.objects.get_or_create(name="Velký sál")
        for row in range(1, 6):
            for number in range(1, 11):
                Seat.objects.get_or_create(hall=hall, row=row, number=number)
        Seat.objects.filter(hall=hall, row=5, number=10).update(is_active=False)

        start = timezone.localtime().replace(hour=19, minute=0, second=0, microsecond=0)
        plays = [
            ("Hamlet", "Tragédie o dánském princi.", timedelta(hours=3), [2, 9]),
            ("Lakomec", "Komedie o skrblíkovi Harpagonovi.", timedelta(hours=2), [5]),
        ]
        for title, description, duration, days in plays:
            play, _ = Play.objects.get_or_create(
                title=title, defaults={"description": description, "duration": duration}
            )
            for day in days:
                Performance.objects.get_or_create(
                    play=play, hall=hall, start_at=start + timedelta(days=day)
                )

        user, created = get_user_model().objects.get_or_create(username="demo")
        if created:
            user.set_password("demo")
            user.save()
        self.stdout.write("Demo data ready; log in as demo / demo.")
