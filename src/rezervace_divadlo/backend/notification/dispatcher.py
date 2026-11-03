"""Claim -> commit -> send -> mark. External I/O never holds a DB transaction.

Delivery is at-least-once. A crash after send may cause a duplicate with the
same ID. Expired claims are reclaimed; tokens fence off late worker results.
"""

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string

from .adapters import NotificationMessage, NotificationSender
from .models import NotificationRequest

logger = logging.getLogger(__name__)


def _claim():
    now = timezone.now()
    with transaction.atomic():
        available = NotificationRequest.objects.filter(
            status=NotificationRequest.Status.PENDING,
            next_attempt_at__lte=now,
        ).filter(Q(claimed_until__isnull=True) | Q(claimed_until__lte=now))
        # A crash during the final attempt must not leave an immortal PENDING row.
        swept_failed = available.filter(
            attempts__gte=settings.NOTIFICATION_MAX_ATTEMPTS
        ).update(
            status=NotificationRequest.Status.FAILED,
            claim_token=None, claimed_until=None,
            last_error="Delivery attempt limit reached; last worker may have stopped before acknowledgement.",
        )
        item = available.select_for_update().order_by("next_attempt_at", "created_at", "pk").first()
        if item is None:
            return None, swept_failed
        token = uuid.uuid4()
        # Conditional update also prevents two claimants from owning the same row.
        updated = available.filter(pk=item.pk, attempts=item.attempts).update(
            attempts=item.attempts + 1,
            claim_token=token,
            claimed_until=now + timedelta(seconds=settings.NOTIFICATION_LEASE_SECONDS),
        )
        if not updated:
            return None, swept_failed
        item.attempts += 1
        item.claim_token = token
        return item, swept_failed


def dispatch_notifications(*, batch_size=100, sender: NotificationSender | None = None):
    """Attempt up to batch_size due deliveries; return attempted/sent/retried/failed counts."""
    if connection.in_atomic_block:
        raise RuntimeError("Dispatch must run outside a transaction")
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    for name in ("NOTIFICATION_MAX_ATTEMPTS", "NOTIFICATION_BACKOFF_SECONDS",
                 "NOTIFICATION_MAX_BACKOFF_SECONDS", "NOTIFICATION_TIMEOUT_SECONDS",
                 "NOTIFICATION_LEASE_SECONDS"):
        if getattr(settings, name) <= 0:
            raise ValueError(f"{name} must be positive")
    if settings.NOTIFICATION_LEASE_SECONDS <= settings.NOTIFICATION_TIMEOUT_SECONDS:
        raise ValueError("Notification lease must exceed the sender timeout")
    if sender is None:
        sender = import_string(settings.NOTIFICATION_SENDER)()
    counts = dict(attempted=0, sent=0, retried=0, failed=0)
    for _ in range(batch_size):
        item, swept_failed = _claim()
        counts["failed"] += swept_failed
        if item is None:
            break
        counts["attempted"] += 1
        owned = NotificationRequest.objects.filter(
            pk=item.pk, status=NotificationRequest.Status.PENDING,
            claim_token=item.claim_token,
        )
        try:
            sender.send(NotificationMessage(
                id=str(item.pk), reservation_id=item.reservation_id,
                event=item.event, payload=item.payload,
            ))
        except Exception as error:
            exhausted = item.attempts >= settings.NOTIFICATION_MAX_ATTEMPTS
            delay = settings.NOTIFICATION_BACKOFF_SECONDS
            for _ in range(item.attempts - 1):
                delay = min(delay * 2, settings.NOTIFICATION_MAX_BACKOFF_SECONDS)
                if delay == settings.NOTIFICATION_MAX_BACKOFF_SECONDS:
                    break
            delay = min(delay, settings.NOTIFICATION_MAX_BACKOFF_SECONDS)
            updated = owned.update(
                status=NotificationRequest.Status.FAILED if exhausted else NotificationRequest.Status.PENDING,
                next_attempt_at=timezone.now() + timedelta(seconds=delay),
                claim_token=None, claimed_until=None, last_error=str(error)[:2000],
            )
            if updated:
                counts["failed" if exhausted else "retried"] += 1
            logger.warning("Notification %s attempt %s failed: %s", item.pk, item.attempts, error)
        else:
            updated = owned.update(
                status=NotificationRequest.Status.SENT, sent_at=timezone.now(),
                claim_token=None, claimed_until=None, last_error="",
            )
            counts["sent"] += updated
    return counts
