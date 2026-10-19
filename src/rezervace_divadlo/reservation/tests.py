from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from notification.dispatcher import dispatch_notifications
from notification.models import NotificationRequest

from . import services
from .models import Hall, Performance, Play, Reservation, Seat
from .services import (
    ReservationError,
    approve_reservation,
    cancel_reservation,
    check_availability,
    confirm_reservation,
    create_reservation,
    expire_reservations,
    touch_reservation,
)


class ReservationFixture:
    def setUp(self):
        self.now = timezone.now().replace(microsecond=0)
        self.user = get_user_model().objects.create_user(username="visitor")
        self.other_user = get_user_model().objects.create_user(username="other")
        self.approver = get_user_model().objects.create_user(username="approver")
        self.approver.user_permissions.add(
            Permission.objects.get(codename="approve_reservation")
        )
        self.hall = Hall.objects.create(name="Main Hall")
        self.seats = [
            Seat.objects.create(hall=self.hall, row=1, number=number)
            for number in range(1, 21)
        ]
        self.play = Play.objects.create(title="Hamlet", duration=timedelta(hours=2))
        self.performance = Performance.objects.create(
            hall=self.hall, play=self.play, start_at=self.now + timedelta(days=2)
        )

    def create(self, count=1):
        return create_reservation(
            self.user, self.performance.pk,
            [seat.pk for seat in self.seats[:count]], now=self.now,
        )


class ReservationTests(ReservationFixture, TestCase):
    def test_create_confirm_cancel_preserves_history_and_releases_seats(self):
        reservation = self.create(3)
        loaded = Reservation.objects.get(pk=reservation.pk)
        self.assertEqual(loaded.status, Reservation.Status.DRAFT)
        self.assertEqual(loaded.seats.count(), 3)
        self.assertEqual(loaded.performance.play, self.play)
        self.assertFalse(check_availability(self.performance.pk, now=self.now)[self.seats[0].pk])

        confirmed = confirm_reservation(self.user, reservation.pk, now=self.now)
        self.assertEqual(confirmed.status, Reservation.Status.CONFIRMED)
        cancelled = cancel_reservation(self.user, reservation.pk, now=self.now)
        self.assertEqual(cancelled.status, Reservation.Status.CANCELLED)
        self.assertEqual(cancelled.seats.count(), 3)
        self.assertTrue(check_availability(self.performance.pk, now=self.now)[self.seats[0].pk])
        self.assertNotEqual(self.create(3).pk, reservation.pk)

    def test_empty_duplicate_and_unknown_seats_are_rejected(self):
        for seat_ids in ([], [self.seats[0].pk] * 2, [999999]):
            with self.subTest(seat_ids=seat_ids):
                with self.assertRaises(ReservationError):
                    create_reservation(self.user, self.performance.pk, seat_ids, now=self.now)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_wrong_hall_and_inactive_seat_are_rejected(self):
        other_hall = Hall.objects.create(name="Other Hall")
        other_seat = Seat.objects.create(hall=other_hall, row=1, number=1)
        with self.assertRaises(ReservationError):
            create_reservation(self.user, self.performance.pk, [other_seat.pk], now=self.now)
        self.seats[0].is_active = False
        self.seats[0].save()
        with self.assertRaises(ReservationError):
            self.create()
        self.assertEqual(Reservation.objects.count(), 0)

    def test_one_occupied_seat_rejects_entire_selection(self):
        create_reservation(self.user, self.performance.pk, [self.seats[1].pk], now=self.now)
        with self.assertRaises(ReservationError) as error:
            self.create(3)
        self.assertEqual(error.exception.code, "unavailable")
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertTrue(check_availability(self.performance.pk, now=self.now)[self.seats[0].pk])

    def test_create_is_rejected_exactly_fifteen_minutes_before_start(self):
        self.performance.start_at = self.now + timedelta(minutes=15)
        self.performance.save()
        with self.assertRaises(ReservationError) as error:
            self.create()
        self.assertEqual(error.exception.code, "too_late")
        self.performance.start_at += timedelta(seconds=1)
        self.performance.save()
        self.assertEqual(self.create().status, Reservation.Status.DRAFT)

    def test_bulk_create_requires_at_least_twenty_four_hours(self):
        self.performance.start_at = self.now + timedelta(hours=24, seconds=-1)
        self.performance.save()
        with self.assertRaises(ReservationError) as error:
            self.create(11)
        self.assertEqual(error.exception.code, "approval_too_late")
        self.performance.start_at += timedelta(seconds=1)
        self.performance.save()
        self.assertEqual(self.create(11).status, Reservation.Status.DRAFT)

    def test_bulk_confirm_also_requires_twenty_four_hours(self):
        self.performance.start_at = self.now + timedelta(hours=24, seconds=1)
        self.performance.save()
        reservation = self.create(11)
        with self.assertRaises(ReservationError) as error:
            confirm_reservation(self.user, reservation.pk, now=self.now + timedelta(seconds=2))
        self.assertEqual(error.exception.code, "approval_too_late")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.DRAFT)

    def test_ten_seats_confirm_directly_but_eleven_require_approval(self):
        reservation = self.create(10)
        self.assertEqual(
            confirm_reservation(self.user, reservation.pk, now=self.now).status,
            Reservation.Status.CONFIRMED,
        )
        cancel_reservation(self.user, reservation.pk, now=self.now)
        bulk = self.create(11)
        self.assertEqual(
            confirm_reservation(self.user, bulk.pk, now=self.now).status,
            Reservation.Status.PENDING_APPROVAL,
        )

    def test_entire_small_hall_requires_approval(self):
        Seat.objects.filter(hall=self.hall, number__gt=2).delete()
        reservation = self.create(2)
        result = confirm_reservation(self.user, reservation.pk, now=self.now)
        self.assertEqual(result.status, Reservation.Status.PENDING_APPROVAL)

    def test_anonymous_user_and_other_owner_cannot_change_reservation(self):
        with self.assertRaises(ReservationError):
            create_reservation(AnonymousUser(), self.performance.pk, [self.seats[0].pk], now=self.now)
        reservation = self.create()
        for operation in (confirm_reservation, cancel_reservation):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(ReservationError) as error:
                    operation(self.other_user, reservation.pk, now=self.now)
                self.assertEqual(error.exception.code, "forbidden")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.DRAFT)

    def test_confirm_at_hold_deadline_expires_reservation(self):
        reservation = self.create()
        with self.assertRaises(ReservationError) as error:
            confirm_reservation(self.user, reservation.pk, now=reservation.hold_until)
        self.assertEqual(error.exception.code, "expired")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertFalse(reservation.allocations.filter(active=True).exists())

    def test_confirm_cannot_be_repeated(self):
        reservation = self.create()
        confirm_reservation(self.user, reservation.pk, now=self.now)
        with self.assertRaises(ReservationError) as error:
            confirm_reservation(self.user, reservation.pk, now=self.now)
        self.assertEqual(error.exception.code, "invalid_state")

    def test_repeated_cancel_succeeds_even_after_start(self):
        reservation = self.create()
        cancel_reservation(self.user, reservation.pk, now=self.now)
        result = cancel_reservation(self.user, reservation.pk, now=self.performance.start_at)
        self.assertEqual(result.status, Reservation.Status.CANCELLED)
        self.assertEqual(result.seats.count(), 1)

    def test_first_cancel_at_start_is_rejected(self):
        reservation = self.create()
        confirm_reservation(self.user, reservation.pk, now=self.now)
        with self.assertRaises(ReservationError) as error:
            cancel_reservation(self.user, reservation.pk, now=self.performance.start_at)
        self.assertEqual(error.exception.code, "too_late")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)

    def test_only_approver_can_decide_and_rejection_releases_seats(self):
        reservation = self.create(11)
        confirm_reservation(self.user, reservation.pk, now=self.now)
        with self.assertRaises(ReservationError) as error:
            approve_reservation(self.user, reservation.pk, now=self.now)
        self.assertEqual(error.exception.code, "forbidden")
        rejected = approve_reservation(self.approver, reservation.pk, approve=False, now=self.now)
        self.assertEqual(rejected.status, Reservation.Status.REJECTED)
        self.assertTrue(check_availability(self.performance.pk, now=self.now)[self.seats[0].pk])
        with self.assertRaises(ReservationError):
            approve_reservation(self.approver, reservation.pk, now=self.now)

    def test_approval_just_before_deadline_succeeds(self):
        reservation = self.create(11)
        pending = confirm_reservation(self.user, reservation.pk, now=self.now)
        approved = approve_reservation(
            self.approver, reservation.pk, now=pending.approval_deadline - timedelta(seconds=1)
        )
        self.assertEqual(approved.status, Reservation.Status.CONFIRMED)

    def test_approval_at_deadline_expires_reservation(self):
        reservation = self.create(11)
        pending = confirm_reservation(self.user, reservation.pk, now=self.now)
        with self.assertRaises(ReservationError):
            approve_reservation(self.approver, reservation.pk, now=pending.approval_deadline)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertFalse(reservation.allocations.filter(active=True).exists())

    def test_availability_treats_touching_intervals_as_available(self):
        self.create()
        start = self.performance.start_at
        end = start + self.play.duration
        for query_start, query_end, expected in (
            (start - timedelta(hours=1), start, True),
            (start, end, False),
            (end, end + timedelta(hours=1), True),
        ):
            with self.subTest(start=query_start):
                result = check_availability(
                    self.performance.pk, start=query_start, end=query_end, now=self.now
                )
                self.assertEqual(result[self.seats[0].pk], expected)
        with self.assertRaises(ReservationError):
            check_availability(self.performance.pk, start=start, end=start, now=self.now)

    def test_activity_extends_hold_and_expiration_is_idempotent(self):
        reservation = self.create()
        renewed = touch_reservation(self.user, reservation.pk, now=self.now + timedelta(minutes=4))
        deadline = self.now + timedelta(minutes=9)
        self.assertEqual(renewed.hold_until, deadline)
        self.assertEqual(expire_reservations(now=deadline - timedelta(seconds=1)), 0)
        self.assertEqual(expire_reservations(now=deadline), 1)
        self.assertEqual(expire_reservations(now=deadline), 0)
        with self.assertRaises(ReservationError):
            touch_reservation(self.user, reservation.pk, now=deadline)

    def test_confirmation_enqueues_notification_without_inline_delivery(self):
        from unittest.mock import patch
        from notification.models import NotificationRequest

        reservation = self.create(11)
        with patch("notification.adapters.LoggingSender.send") as send:
            confirm_reservation(self.user, reservation.pk, now=self.now)
        send.assert_not_called()
        item = NotificationRequest.objects.get(reservation_id=reservation.pk)
        self.assertEqual(item.event, "approval_requested")
        self.assertEqual(item.status, NotificationRequest.Status.PENDING)
        self.assertEqual(item.payload["status"], Reservation.Status.PENDING_APPROVAL)

    def test_outbox_record_and_status_change_share_one_transaction(self):
        record = services.record_notification

        def crash_after_insert(reservation, event):
            record(reservation, event)
            raise RuntimeError("crash before commit")

        for name, failure in (("crash after outbox insert", crash_after_insert),
                              ("outbox insert fails", RuntimeError("outbox unavailable"))):
            with self.subTest(name):
                reservation = self.create(11)
                with patch("reservation.services.record_notification", side_effect=failure), \
                        self.assertRaises(RuntimeError):
                    confirm_reservation(self.user, reservation.pk, now=self.now)
                reservation.refresh_from_db()
                self.assertEqual(reservation.status, Reservation.Status.DRAFT)
                self.assertIsNone(reservation.approval_deadline)
                self.assertFalse(NotificationRequest.objects.exists())
                cancel_reservation(self.user, reservation.pk, now=self.now)

    def test_decision_and_expiry_enqueue_owner_notifications(self):
        rejected = self.create(11)
        confirm_reservation(self.user, rejected.pk, now=self.now)
        approve_reservation(self.approver, rejected.pk, approve=False, now=self.now)
        expired = self.create(11)
        pending = confirm_reservation(self.user, expired.pk, now=self.now)
        expire_reservations(now=pending.approval_deadline)
        for reservation, event in ((rejected, "rejected"), (expired, "expired")):
            with self.subTest(event=event):
                items = NotificationRequest.objects.filter(reservation_id=reservation.pk)
                self.assertEqual(
                    {(item.event, item.payload["audience"]) for item in items},
                    {("approval_requested", "approvers"), (event, "owner")},
                )


class ReservationNotificationFlowTests(ReservationFixture, TransactionTestCase):
    # The dispatcher refuses to run inside a transaction, so TestCase cannot host this flow.
    def test_committed_transitions_are_delivered_through_sender(self):
        reservation = self.create(11)
        confirm_reservation(self.user, reservation.pk, now=self.now)
        approve_reservation(self.approver, reservation.pk, now=self.now)
        sender = Mock()
        self.assertEqual(dispatch_notifications(sender=sender),
                         dict(attempted=2, sent=2, retried=0, failed=0))
        messages = {call.args[0].event: call.args[0] for call in sender.send.call_args_list}
        self.assertEqual(set(messages), {"approval_requested", "approved"})
        for event, audience, status in (
            ("approval_requested", "approvers", Reservation.Status.PENDING_APPROVAL),
            ("approved", "owner", Reservation.Status.CONFIRMED),
        ):
            with self.subTest(event=event):
                message = messages[event]
                self.assertEqual(message.reservation_id, reservation.pk)
                self.assertEqual(message.payload, dict(
                    owner_id=self.user.pk, performance_id=self.performance.pk,
                    status=status, audience=audience,
                ))
                item = NotificationRequest.objects.get(pk=message.id)
                self.assertEqual(item.status, NotificationRequest.Status.SENT)
        self.assertEqual(dispatch_notifications(sender=sender)["attempted"], 0)
