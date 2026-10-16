import uuid

from django.db import models
from django.utils import timezone


class NotificationRequest(models.Model):
    """Durable delivery request; payload is a snapshot of the committed event."""

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SENT = "SENT"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_id = models.PositiveBigIntegerField()
    event = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    claim_token = models.UUIDField(null=True, blank=True, editable=False)
    claimed_until = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"], name="notification_due_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["PENDING", "SENT", "FAILED"]),
                name="notification_valid_status",
            ),
            models.CheckConstraint(
                condition=(models.Q(claim_token__isnull=True, claimed_until__isnull=True)
                           | models.Q(claim_token__isnull=False, claimed_until__isnull=False)),
                name="notification_valid_claim",
            ),
        ]
