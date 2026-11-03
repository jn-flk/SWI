from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Performance, Play, Reservation
from .services import create_reservation
from .tests import ReservationFixture


class FrontendTests(ReservationFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.seats_url = reverse("seat_selection", args=[self.performance.pk])

    def select(self, *seats):
        return self.client.post(self.seats_url, {"seats": [seat.pk for seat in seats]})

    def url(self, name, reservation):
        return reverse(name, args=[reservation.pk])

    def test_list_shows_only_upcoming_performances_in_shared_layout(self):
        past_play = Play.objects.create(title="Minulá hra", duration=timedelta(hours=1))
        Performance.objects.create(
            hall=self.hall, play=past_play, start_at=self.now - timedelta(days=1)
        )
        response = self.client.get(reverse("performance_list"))
        for template in ("base.html", "components/header.html", "components/footer.html"):
            self.assertTemplateUsed(response, template)
        self.assertContains(response, "Hamlet")
        self.assertNotContains(response, "Minulá hra")

    def test_seat_selection_requires_login(self):
        self.client.logout()
        response = self.client.get(self.seats_url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.seats_url}")

    def test_blocked_and_inactive_seats_are_shown_unavailable(self):
        self.create(1)
        self.seats[1].is_active = False
        self.seats[1].save()
        response = self.client.get(self.seats_url)
        available = {
            item["seat"].pk: item["available"]
            for _, seats in response.context["rows"] for item in seats
        }
        self.assertFalse(available[self.seats[0].pk])
        self.assertFalse(available[self.seats[1].pk])
        self.assertTrue(available[self.seats[2].pk])

    def test_unavailable_seat_cannot_be_reserved(self):
        self.create(1)
        response = self.select(self.seats[0])
        self.assertFormError(
            response.context["form"], "seats", "Vybrané sedadlo už není dostupné."
        )
        self.assertEqual(Reservation.objects.count(), 1)

    def test_service_error_is_shown_in_form(self):
        self.performance.start_at = timezone.now() + timedelta(minutes=10)
        self.performance.save()
        response = self.select(self.seats[0])
        self.assertFormError(
            response.context["form"], None, "Rezervace nelze přijmout 15 minut před začátkem."
        )
        self.assertEqual(Reservation.objects.count(), 0)

    def test_full_flow_confirms_reservation(self):
        response = self.select(self.seats[0], self.seats[1])
        reservation = Reservation.objects.get()
        self.assertRedirects(response, self.url("reservation_form", reservation))

        response = self.client.post(self.url("reservation_form", reservation), {
            "first_name": "Jan", "last_name": "Novák", "email": "jan@example.com",
        })
        summary_url = self.url("reservation_summary", reservation)
        self.assertRedirects(response, summary_url)
        self.assertContains(self.client.get(summary_url), "Jan Novák")

        response = self.client.post(summary_url)
        self.assertRedirects(response, self.url("reservation_success", reservation))
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.seats.count(), 2)

    def test_invalid_contact_form_shows_errors_and_keeps_draft(self):
        reservation = self.create(1)
        response = self.client.post(self.url("reservation_form", reservation), {
            "first_name": "", "last_name": "Novák", "email": "neplatny",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), {"first_name", "email"})
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.DRAFT)

    def test_expired_hold_cannot_be_confirmed(self):
        reservation = create_reservation(
            self.user, self.performance.pk, [self.seats[0].pk],
            now=timezone.now() - timedelta(minutes=6),
        )
        response = self.client.post(self.url("reservation_summary", reservation))
        self.assertRedirects(response, self.seats_url)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)

    def test_other_users_reservation_is_not_found(self):
        reservation = self.create(1)
        self.client.force_login(self.other_user)
        for name in ("reservation_form", "reservation_summary", "reservation_success"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(self.url(name, reservation)).status_code, 404)
