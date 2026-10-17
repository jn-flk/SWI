"""Delivery contracts and recovery behavior, without contacting an external service."""

import json
import uuid
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from .adapters import HttpSender, LoggingSender, NotificationMessage
from .dispatcher import dispatch_notifications
from .models import NotificationRequest
from .services import record_notification


class RecordNotificationContractTests(TransactionTestCase):
    # Not TestCase: its wrapping transaction would hide the outside-transaction precondition.
    def setUp(self):
        # Stub instead of a Reservation row: the contract only reads these four fields.
        self.reservation = SimpleNamespace(pk=11, owner_id=7, performance_id=3,
                                           status="PENDING_APPROVAL")

    def test_recording_outside_transaction_is_rejected_without_writing(self):
        with self.assertRaisesMessage(RuntimeError, "reservation transaction"):
            record_notification(self.reservation, "approval_requested")
        self.assertFalse(NotificationRequest.objects.exists())

    def test_unsupported_event_is_rejected_without_writing(self):
        with transaction.atomic(), self.assertRaisesMessage(ValueError, "cancelled"):
            record_notification(self.reservation, "cancelled")
        self.assertFalse(NotificationRequest.objects.exists())

    def test_snapshot_and_audience_follow_event(self):
        for event, audience in [("approval_requested", "approvers"), ("approved", "owner"),
                                ("rejected", "owner"), ("expired", "owner")]:
            with self.subTest(event=event):
                with transaction.atomic():
                    item = record_notification(self.reservation, event)
                item.refresh_from_db()
                self.assertEqual(item.reservation_id, 11)
                self.assertEqual(item.event, event)
                self.assertEqual(item.status, NotificationRequest.Status.PENDING)
                self.assertEqual(item.attempts, 0)
                self.assertEqual(item.payload, dict(
                    owner_id=7, performance_id=3, status="PENDING_APPROVAL", audience=audience,
                ))


class NotificationDispatchTests(TransactionTestCase):
    # Real commits are needed to verify the claim/send transaction boundary.
    def setUp(self):
        self.now = timezone.now().replace(microsecond=0)
        self.sender = Mock()
        self.clock = patch("notification.dispatcher.timezone.now", return_value=self.now)
        self.mock_now = self.clock.start()
        self.addCleanup(self.clock.stop)

    def request(self, **kwargs):
        defaults = dict(reservation_id=1, event="approval_requested",
                        payload={"audience": "approvers"}, next_attempt_at=self.now)
        defaults.update(kwargs)
        return NotificationRequest.objects.create(**defaults)

    def dispatch(self, **kwargs):
        return dispatch_notifications(sender=self.sender, **kwargs)

    def test_outbox_record_is_rolled_back_with_its_transaction(self):
        with self.assertRaisesMessage(RuntimeError, "abort"):
            with transaction.atomic():
                self.request()
                raise RuntimeError("abort")
        self.assertFalse(NotificationRequest.objects.exists())

    def test_success_sends_snapshot_outside_transaction_and_marks_sent(self):
        item = self.request()

        def send(message):
            self.assertFalse(connection.in_atomic_block)
            claimed = NotificationRequest.objects.get(pk=item.pk)
            self.assertEqual(claimed.status, NotificationRequest.Status.PENDING)
            self.assertEqual(claimed.attempts, 1)
            self.assertIsNotNone(claimed.claim_token)
            self.assertEqual(message, NotificationMessage(
                str(item.pk), 1, "approval_requested", {"audience": "approvers"},
            ))

        self.sender.send.side_effect = send
        self.assertEqual(self.dispatch(), dict(attempted=1, sent=1, retried=0, failed=0))
        item.refresh_from_db()
        self.assertEqual(item.status, NotificationRequest.Status.SENT)
        self.assertEqual(item.sent_at, self.now)
        self.assertIsNone(item.claim_token)
        self.assertIsNone(item.claimed_until)
        self.assertEqual(item.last_error, "")
        self.dispatch()
        self.sender.send.assert_called_once()

    def test_future_terminal_and_unexpired_claims_are_not_delivered(self):
        self.request(next_attempt_at=self.now + timedelta(seconds=1))
        self.request(status=NotificationRequest.Status.SENT)
        self.request(status=NotificationRequest.Status.FAILED)
        self.request(claim_token=uuid.uuid4(), claimed_until=self.now + timedelta(seconds=1))
        self.assertEqual(self.dispatch()["attempted"], 0)
        self.sender.send.assert_not_called()

    def test_failure_schedules_retry_at_exact_deadline_with_stable_id(self):
        item = self.request()
        self.sender.send.side_effect = [TimeoutError("service timeout"), None]
        with self.assertLogs("notification.dispatcher", level="WARNING"):
            self.assertEqual(self.dispatch()["retried"], 1)
        item.refresh_from_db()
        self.assertEqual(item.status, NotificationRequest.Status.PENDING)
        self.assertEqual(item.attempts, 1)
        self.assertEqual(item.next_attempt_at, self.now + timedelta(seconds=10))
        self.assertEqual(item.last_error, "service timeout")
        self.assertIsNone(item.claim_token)
        self.assertIsNone(item.claimed_until)
        self.now += timedelta(seconds=9)
        self.mock_now.return_value = self.now
        self.assertEqual(self.dispatch()["attempted"], 0)
        self.now += timedelta(seconds=1)
        self.mock_now.return_value = self.now
        self.assertEqual(self.dispatch()["sent"], 1)
        messages = [call.args[0] for call in self.sender.send.call_args_list]
        self.assertEqual([message.id for message in messages], [str(item.pk)] * 2)
        item.refresh_from_db()
        self.assertEqual(item.attempts, 2)
        self.assertEqual(item.last_error, "")

    @override_settings(NOTIFICATION_MAX_ATTEMPTS=10, NOTIFICATION_MAX_BACKOFF_SECONDS=25)
    def test_backoff_doubles_and_is_capped(self):
        for attempts, delay in [(0, 10), (1, 20), (2, 25), (7, 25)]:
            with self.subTest(attempts=attempts):
                item = self.request(attempts=attempts)
                self.sender.send.side_effect = RuntimeError("offline")
                with self.assertLogs("notification.dispatcher", level="WARNING"):
                    self.dispatch()
                item.refresh_from_db()
                self.assertEqual(item.next_attempt_at, self.now + timedelta(seconds=delay))

    def test_final_failure_stops_retries(self):
        item = self.request(attempts=4)
        self.sender.send.side_effect = RuntimeError("offline")
        with self.assertLogs("notification.dispatcher", level="WARNING"):
            self.assertEqual(self.dispatch()["failed"], 1)
        item.refresh_from_db()
        self.assertEqual(item.status, NotificationRequest.Status.FAILED)
        self.assertEqual(item.attempts, 5)
        self.assertIsNone(item.claim_token)
        self.dispatch()
        self.sender.send.assert_called_once()

    def test_expired_lease_is_recovered_with_same_message_id(self):
        old_token = uuid.uuid4()
        item = self.request(attempts=1, claim_token=old_token, claimed_until=self.now)

        def send(message):
            claimed = NotificationRequest.objects.get(pk=item.pk)
            self.assertNotEqual(claimed.claim_token, old_token)
            self.assertEqual(message.id, str(item.pk))

        self.sender.send.side_effect = send
        self.assertEqual(self.dispatch()["sent"], 1)
        item.refresh_from_db()
        self.assertEqual(item.attempts, 2)

    def test_crash_on_last_attempt_becomes_failed_without_another_send(self):
        item = self.request(attempts=5, claim_token=uuid.uuid4(), claimed_until=self.now)
        self.dispatch()
        item.refresh_from_db()
        self.assertEqual(item.status, NotificationRequest.Status.FAILED)
        self.assertIn("last worker", item.last_error)
        self.assertIsNone(item.claim_token)
        self.sender.send.assert_not_called()

    def test_late_worker_cannot_overwrite_new_claim_on_success_or_failure(self):
        for error in (None, TimeoutError("late timeout")):
            with self.subTest(error=error):
                item = self.request()
                replacement = uuid.uuid4()

                def send(message):
                    NotificationRequest.objects.filter(pk=item.pk).update(
                        claim_token=replacement, claimed_until=self.now + timedelta(seconds=120),
                    )
                    if error:
                        raise error

                self.sender.send.side_effect = send
                if error:
                    with self.assertLogs("notification.dispatcher", level="WARNING"):
                        counts = self.dispatch(batch_size=1)
                else:
                    counts = self.dispatch(batch_size=1)
                item.refresh_from_db()
                self.assertEqual(item.status, NotificationRequest.Status.PENDING)
                self.assertEqual(item.claim_token, replacement)
                self.assertIsNone(item.sent_at)
                self.assertEqual(counts, dict(attempted=1, sent=0, retried=0, failed=0))

    def test_batch_limit_leaves_remaining_work_pending(self):
        for _ in range(3):
            self.request()
        self.assertEqual(self.dispatch(batch_size=2)["sent"], 2)
        self.assertEqual(NotificationRequest.objects.filter(status="PENDING").count(), 1)

    def test_dispatch_inside_transaction_is_rejected_before_sending(self):
        self.request()
        with transaction.atomic(), self.assertRaisesMessage(RuntimeError, "outside a transaction"):
            self.dispatch()
        self.sender.send.assert_not_called()

    def test_invalid_batch_sizes_are_rejected(self):
        for size in (0, -1, True, 1.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.dispatch(batch_size=size)

    @override_settings(NOTIFICATION_LEASE_SECONDS=5, NOTIFICATION_TIMEOUT_SECONDS=5)
    def test_lease_must_exceed_delivery_timeout(self):
        with self.assertRaisesMessage(ValueError, "lease must exceed"):
            self.dispatch()


@override_settings(NOTIFICATION_SERVICE_URL="https://notifications.example/events",
                   NOTIFICATION_TIMEOUT_SECONDS=5)
class NotificationAdapterTests(SimpleTestCase):
    def setUp(self):
        self.message = NotificationMessage("stable-id", 42, "approved", {"owner_id": 7})

    @patch("notification.adapters.urlopen")
    def test_http_posts_snapshot_with_idempotency_key_and_timeout(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 202
        HttpSender().send(self.message)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://notifications.example/events")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Idempotency-key"), "stable-id")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(request.data), dict(
            id="stable-id", reservation_id=42, event="approved", payload={"owner_id": 7},
        ))
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)

    @patch("notification.adapters.urlopen")
    def test_http_transport_and_server_errors_propagate_for_retry(self, urlopen):
        for error in (URLError("offline"), HTTPError("https://notifications.example", 503,
                                                   "Unavailable", {}, None)):
            with self.subTest(error=error):
                urlopen.side_effect = error
                with self.assertRaises(type(error)):
                    HttpSender().send(self.message)

    @patch("notification.adapters.urlopen")
    def test_http_non_success_response_is_rejected(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 300
        with self.assertRaisesMessage(RuntimeError, "HTTP 300"):
            HttpSender().send(self.message)

    @override_settings(NOTIFICATION_SERVICE_URL="")
    @patch("notification.adapters.urlopen")
    def test_http_requires_endpoint_before_attempting_network(self, urlopen):
        with self.assertRaisesMessage(ValueError, "NOTIFICATION_SERVICE_URL"):
            HttpSender().send(self.message)
        urlopen.assert_not_called()

    def test_logging_adapter_records_message_identity_and_event(self):
        with self.assertLogs("notification.adapters", level="INFO") as logs:
            LoggingSender().send(self.message)
        self.assertIn("stable-id", logs.output[0])
        self.assertIn("approved", logs.output[0])


class NotificationCommandTests(SimpleTestCase):
    @patch("notification.management.commands.dispatch_notifications.dispatch_notifications")
    def test_one_shot_command_dispatches_and_prints_counts(self, dispatch):
        dispatch.return_value = dict(attempted=2, sent=1, retried=1, failed=0)
        output = StringIO()
        call_command("dispatch_notifications", batch_size=2, stdout=output)
        dispatch.assert_called_once_with(batch_size=2)
        self.assertIn("attempted=2 sent=1 retried=1 failed=0", output.getvalue())

    def test_invalid_command_options_are_rejected(self):
        for options in ({"interval": 0}, {"interval": float("nan")},
                        {"interval": float("inf")}, {"batch_size": 0}):
            with self.subTest(options=options), self.assertRaises(CommandError):
                call_command("dispatch_notifications", **options)
