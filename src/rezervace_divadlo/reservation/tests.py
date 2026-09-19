from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from .models import Hall, Performance, Play, Reservation, Seat


class ReservationPersistenceTest(TestCase):
	def test_reservation_relationships_persist_and_duplicate_is_rejected(self):
		play = Play.objects.create(
			title="Hamlet",
			description="A theatre play",
			duration=timedelta(hours=2),
		)
		hall = Hall.objects.create(name="Main Hall")
		seat = Seat.objects.create(hall=hall, row=1, number=1)
		performance = Performance.objects.create(
			play=play,
			hall=hall,
			start_at=timezone.now(),
		)

		print("Creating first reservation...")

		reservation = Reservation.objects.create(
			performance=performance,
			seat=seat,
		)

		print("Reservation created with ID:", reservation.pk)
		print("Loading reservation again from database...")

		loaded_reservation = Reservation.objects.get(pk=reservation.pk)

		print(f"Reservation loaded with ID: {loaded_reservation.pk}")
		print(f"Performance: {loaded_reservation.performance}")
		print(f"Play: {loaded_reservation.performance.play}")
		print(f"Hall: {loaded_reservation.performance.hall}")
		print(f"Seat: {loaded_reservation.seat}")
	
		self.assertEqual(loaded_reservation.performance.play, play)
		self.assertEqual(loaded_reservation.performance.hall, hall)
		self.assertEqual(loaded_reservation.seat, seat)
		self.assertEqual(loaded_reservation.seat.hall, hall)

		print("Trying to create duplicate reservation...")
		
		with self.assertRaises(IntegrityError):
			Reservation.objects.create(performance=performance, seat=seat)

		print("Duplicate reservation rejected.")